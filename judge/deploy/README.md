# Setting up the judge machine

The judge runs players' code. It needs Docker, so it lives on its own Linux machine. This is the whole setup, step by step.

## What you need
1. A small Linux machine with a public IP address: Ubuntu 22.04 or 24.04, 2 CPUs and 4 GB of memory is plenty to start (for example Oracle Cloud's free
   ARM or AMD VM, or any cheap VPS). **Use it for the judge only.** The judge controls Docker, and Docker is root on the machine, so nothing else
   (no database, no website, no keys, nothing personal) may live there.
2. SSH access with a key (not a password).

## Step 1: Get the code onto the machine
```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/Sayan59das/CompileX.git
cd CompileX/judge/deploy
```

## Step 2: Prepare the machine (Docker, firewall, automatic updates)
```bash
sudo bash setup-host.sh
```
It installs Docker, lets in only ports 22, 80 and 443, turns on automatic security updates, and downloads the four sandbox images. It does not change SSH.

If the machine is on Oracle Cloud, also open ports 80 and 443 in the cloud's own network rules (the "security list"): the machine's firewall is not the only one.

## Step 3: Fill in the settings
```bash
cp .env.example .env
nano .env
```
1. `JUDGE_TOKEN`: the secret. Make one with `openssl rand -hex 24` and paste it. Keep a copy: the website's backend needs the same one.
2. `JUDGE_DOMAIN`: the machine's IP with dashes plus `.sslip.io`. The IP `203.0.113.5` becomes `203-0-113-5.sslip.io`. It points back at the
   machine, so you need no domain of your own, and Caddy gets a free HTTPS certificate for it.

## Step 4: Start it
```bash
docker compose up -d --build
docker compose ps
```
Both services should say running. Check it from your own computer (use your address):
```bash
curl https://203-0-113-5.sslip.io/health
```
You should get `{"status":"ok","docker":true}`. The first request can take a few seconds while the certificate is issued.

## Step 5: Check the secret works and strangers are refused
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://203-0-113-5.sslip.io/run -H "Content-Type: application/json" -d "{}"
```
That must print `401` or `422`, never `200`. Anything not `/run` or `/health` gets `404`.

## Step 6: Tell the website's backend where the judge is (on Render)
In the Render dashboard, open the backend service, then Environment, and add:
1. `JUDGE_URL` = `https://203-0-113-5.sslip.io` (your address)
2. `JUDGE_TOKEN` = the same secret as in step 3

Save. Render redeploys, and Run and Submit start to work.

## Keeping it safe
1. Do not put anything else on this machine, and do not give anyone else a login to it.
2. Never share `JUDGE_TOKEN`. If it leaks, make a new one, change it in `.env` here (`docker compose up -d`) and in Render.
3. Updates: `git pull` then `docker compose up -d --build` in this folder. The operating system updates itself.
4. What the sandboxes do: each submission runs in a fresh container with no internet, 256 MB of memory, at most 128 processes, no extra powers, and as
   an unprivileged user that cannot write system files. The container is deleted afterwards.
5. What this setup cannot stop: a flaw in Docker itself that lets a program escape its container. That is why the machine must hold nothing else and
   why updates are automatic. The worst case then is the loss of the judge machine, not your website or your data.
6. Watch for abuse: `docker compose logs -f judge` shows each request, and `docker stats` shows load.
