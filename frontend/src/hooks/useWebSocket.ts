import { useEffect, useRef, useState } from "react"

export const useWebSocket = (channel: string, onMessage: (data: any) => void) => {
  const ws = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    // Determine WS URL based on current environment
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host
    const wsUrl = `${protocol}//${host}/api/ws`

    const connect = () => {
      ws.current = new WebSocket(wsUrl)

      ws.current.onopen = () => {
        setIsConnected(true)
        console.log(`WebSocket Connected to ${wsUrl}`)
      }

      ws.current.onmessage = (event) => {
        const payload = JSON.parse(event.data)
        if (payload.channel === channel) {
          onMessage(payload.data)
        }
      }

      ws.current.onclose = () => {
        setIsConnected(false)
        console.log("WebSocket Disconnected. Reconnecting in 3s...")
        setTimeout(connect, 3000)
      }

      ws.current.onerror = (err) => {
        console.error("WebSocket Error:", err)
        ws.current?.close()
      }
    }

    connect()

    return () => {
      ws.current?.close()
    }
  }, [channel]) // Re-subscribe if channel changes

  return { isConnected }
}
