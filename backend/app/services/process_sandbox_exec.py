"""Launcher: becomes the player's program, after giving up every privilege. Run only by process_sandbox.py, as root, never by hand.

    python process_sandbox_exec.py UID GID CPU_SECONDS NPROC NOFILE FSIZE_MB DATA_MB WORKDIR -- COMMAND [ARGS...]

In order: new session, move into the work folder, set resource limits, drop to the unprivileged user (and prove root cannot be regained),
forbid gaining privileges, install a syscall filter that refuses internet sockets (and a few dangerous calls), then exec the command.
The filter and the privilege drop are inherited by everything the program starts. If any step fails the program is NOT started.
"""

import ctypes
import os
import struct
import sys

# x86-64 syscall numbers
SYS_SOCKET = 41
SYS_PTRACE = 101
SYS_MOUNT, SYS_UMOUNT2 = 165, 166
SYS_UNSHARE, SYS_SETNS = 272, 308
SYS_PERF_EVENT_OPEN, SYS_BPF = 298, 321
SYS_PROCESS_VM_READV, SYS_PROCESS_VM_WRITEV = 310, 311
SYS_KEYCTL, SYS_ADD_KEY, SYS_REQUEST_KEY = 250, 248, 249
SYS_IO_URING = (425, 426, 427)      # io_uring can open sockets without going through socket(), so it is refused too
DENIED_SYSCALLS = (
    SYS_PTRACE, SYS_MOUNT, SYS_UMOUNT2, SYS_UNSHARE, SYS_SETNS, SYS_PERF_EVENT_OPEN, SYS_BPF,
    SYS_PROCESS_VM_READV, SYS_PROCESS_VM_WRITEV, SYS_KEYCTL, SYS_ADD_KEY, SYS_REQUEST_KEY, *SYS_IO_URING,
)
DENIED_SOCKET_DOMAINS = (2, 10, 17)  # AF_INET, AF_INET6, AF_PACKET. AF_UNIX stays: runtimes use it for themselves and it reaches nothing outside.

AUDIT_ARCH_X86_64 = 0xC000003E
RET_KILL_PROCESS = 0x80000000
RET_ALLOW = 0x7FFF0000
RET_EPERM = 0x00050000 | 1
BPF_LD_W_ABS, BPF_JEQ_K, BPF_RET_K = 0x20, 0x15, 0x06


def build_filter() -> bytes:
    """The classic-BPF program (little-endian `struct sock_filter` records), as bytes. A pure function, so it is testable anywhere.

    Layout (every jump goes forward; a jump counts the instructions to skip after the jump itself):
        0      load the architecture                       4 .. 3+D   one check per denied syscall -> DENY
        1      right architecture? skip the next one       S = 4+D    is it socket()? no -> ALLOW, yes -> next
        2      wrong architecture: kill the process        S+1        load argument 0 (the socket domain)
        3      load the syscall number                     S+2 ..     one check per denied domain -> DENY
                                                           ALLOW      return allow
                                                           DENY       return EPERM
    """
    def stmt(code, k):
        return struct.pack("HBBI", code, 0, 0, k)

    def jeq(k, jt, jf):
        return struct.pack("HBBI", BPF_JEQ_K, jt, jf, k)

    d, k_domains = len(DENIED_SYSCALLS), len(DENIED_SOCKET_DOMAINS)
    socket_idx = 4 + d
    allow_idx = socket_idx + 2 + k_domains
    deny_idx = allow_idx + 1

    ins = [
        stmt(BPF_LD_W_ABS, 4),
        jeq(AUDIT_ARCH_X86_64, 1, 0),
        stmt(BPF_RET_K, RET_KILL_PROCESS),
        stmt(BPF_LD_W_ABS, 0),
    ]
    for i, nr in enumerate(DENIED_SYSCALLS):
        ins.append(jeq(nr, deny_idx - (4 + i) - 1, 0))
    ins.append(jeq(SYS_SOCKET, 0, allow_idx - socket_idx - 1))
    ins.append(stmt(BPF_LD_W_ABS, 16))
    for i, domain in enumerate(DENIED_SOCKET_DOMAINS):
        idx = socket_idx + 2 + i
        ins.append(jeq(domain, deny_idx - idx - 1, 0))
    ins.append(stmt(BPF_RET_K, RET_ALLOW))
    ins.append(stmt(BPF_RET_K, RET_EPERM))
    assert len(ins) == deny_idx + 1
    return b"".join(ins)


class _SockFilter(ctypes.Structure):
    _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte), ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]


class _SockFprog(ctypes.Structure):
    _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.POINTER(_SockFilter))]


def install_filter():
    libc = ctypes.CDLL(None, use_errno=True)
    raw = build_filter()
    count = len(raw) // 8
    array = (_SockFilter * count).from_buffer_copy(raw)
    prog = _SockFprog(count, ctypes.cast(array, ctypes.POINTER(_SockFilter)))
    if libc.prctl(38, 1, 0, 0, 0) != 0:                                            # PR_SET_NO_NEW_PRIVS
        raise OSError(ctypes.get_errno(), "cannot forbid new privileges")
    if libc.prctl(22, 2, ctypes.byref(prog)) != 0:                                 # PR_SET_SECCOMP, SECCOMP_MODE_FILTER
        raise OSError(ctypes.get_errno(), "cannot install the syscall filter")


def main():
    import resource   # Unix only: imported here so build_filter() can be tested on any system

    args = sys.argv[1:]
    sep = args.index("--")
    uid, gid, cpu, nproc, nofile, fsize_mb, data_mb = (int(x) for x in args[:7])
    workdir = args[7]
    command = args[sep + 1:]
    if uid <= 0 or gid <= 0:
        raise SystemExit("refusing to run as root")

    os.setsid()
    os.chdir(workdir)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    resource.setrlimit(resource.RLIMIT_NPROC, (nproc, nproc))
    resource.setrlimit(resource.RLIMIT_NOFILE, (nofile, nofile))
    resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_mb * 1024 * 1024, fsize_mb * 1024 * 1024))
    if data_mb > 0:
        resource.setrlimit(resource.RLIMIT_DATA, (data_mb * 1024 * 1024, data_mb * 1024 * 1024))

    os.setgroups([])
    os.setgid(gid)
    os.setuid(uid)
    try:
        os.setuid(0)
    except PermissionError:
        pass
    else:
        raise SystemExit("could regain root: refusing to run")
    if os.getuid() != uid or os.geteuid() != uid:
        raise SystemExit("privilege drop failed")

    install_filter()
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
