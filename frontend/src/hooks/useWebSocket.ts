import { useEffect, useRef, useState } from "react"

export const useWebSocket = (channel: string, onMessage: (data: any) => void) => {
  const ws = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const onMessageRef = useRef(onMessage)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmounted = useRef(false)

  // Always keep ref up to date
  useEffect(() => {
    onMessageRef.current = onMessage
  }, [onMessage])

  useEffect(() => {
    unmounted.current = false

    // Determine WS URL based on current environment
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws`

    const connect = () => {
      if (unmounted.current) return
      ws.current = new WebSocket(wsUrl)

      ws.current.onopen = () => {
        setIsConnected(true)
      }

      ws.current.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.channel === channel) {
            onMessageRef.current(payload.data)
          }
        } catch {
          // Malformed message — ignore silently
        }
      }

      ws.current.onclose = () => {
        setIsConnected(false)
        if (!unmounted.current) {
          reconnectTimer.current = setTimeout(connect, 3000)
        }
      }

      ws.current.onerror = () => {
        ws.current?.close()
      }
    }

    connect()

    return () => {
      unmounted.current = true
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [channel]) // Re-subscribe if channel changes

  return { isConnected }
}
