import { io } from 'socket.io-client'

let socket = null

// Get the backend URL from environment variable or use relative path for local dev
const getSocketURL = () => {
  // In production, use the API URL without the /api/v1 suffix
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL.replace('/api/v1', '')
  }
  // In local development, use relative path
  return '/'
}

export function getSocket() {
  if (!socket) {
    const url = getSocketURL()
    socket = io(url, { 
      transports: ['websocket', 'polling'],
      autoConnect: false,
      withCredentials: true,
      path: '/socket.io/',
      // The server takes who you are from this token, and refuses a socket without a valid one. It is read on every (re)connect.
      auth: (cb) => cb({ token: localStorage.getItem('token') || '' })
    })
  }
  return socket
}

export function connectSocket() {
  const s = getSocket()
  if (!s.connected) s.connect()
  return s
}

export function disconnectSocket() {
  if (socket?.connected) socket.disconnect()
}
