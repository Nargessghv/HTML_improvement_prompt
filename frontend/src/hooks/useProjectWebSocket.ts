import { useEffect, useRef, useState, useCallback } from 'react'
import { toast } from 'sonner'

export interface WebSocketMessage {
  event_type: string
  project_id?: string
  slide_drafts?: any[]
  workflow_states?: any[]
  project_status?: string
  has_chat_session?: boolean
  chat_session_id?: string
  slide_number?: number
  slide_id?: string
  edit_request_id?: string
  timestamp?: string
  [key: string]: any
}

interface UseProjectWebSocketOptions {
  projectId: string
  onMessage?: (message: WebSocketMessage) => void
  onSlideUpdate?: (slideId: string, data: any) => void
  onWorkflowUpdate?: (state: any) => void
  onError?: (error: Error) => void
  autoReconnect?: boolean
  reconnectInterval?: number
}

export function useProjectWebSocket({
  projectId,
  onMessage,
  onSlideUpdate,
  onWorkflowUpdate,
  onError,
  autoReconnect = true,
  reconnectInterval = 5000
}: UseProjectWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || isConnecting) {
      return
    }

    setIsConnecting(true)

    try {
      // Get auth token
      const token = localStorage.getItem('supabase.auth.token')
      if (!token) {
        throw new Error('No authentication token found')
      }

      // Construct WebSocket URL
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${wsProtocol}//${window.location.host}/ws/${projectId}?token=${encodeURIComponent(token)}`

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setIsConnecting(false)
        
        // Clear any reconnect timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }

        // Send initial ping
        ws.send(JSON.stringify({ type: 'ping' }))
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)

          // Handle specific message types
          switch (message.event_type) {
            case 'initial_state':
              console.log('Received initial state', message)
              break

            case 'slide_generated':
            case 'slide_updated':
            case 'slide_approved':
              if (onSlideUpdate && message.slide_id) {
                onSlideUpdate(message.slide_id, message)
              }
              break

            case 'workflow_update':
              if (onWorkflowUpdate) {
                onWorkflowUpdate(message)
              }
              break

            case 'edit_request_created':
              toast.info('Edit request submitted')
              break

            case 'edit_completed':
              toast.success('Edit completed successfully')
              break

            case 'outline_generated':
            case 'outline_updated':
              toast.success('Presentation outline updated')
              break

            case 'error':
              toast.error(message.error || 'An error occurred')
              break
          }

          // Call general message handler
          if (onMessage) {
            onMessage(message)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsConnecting(false)
        if (onError) {
          onError(new Error('WebSocket connection error'))
        }
      }

      ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason)
        setIsConnected(false)
        setIsConnecting(false)
        wsRef.current = null

        // Auto-reconnect if enabled and not a normal close
        if (autoReconnect && event.code !== 1000) {
          console.log(`Reconnecting in ${reconnectInterval}ms...`)
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        }
      }
    } catch (error) {
      console.error('Error creating WebSocket:', error)
      setIsConnecting(false)
      if (onError) {
        onError(error as Error)
      }
    }
  }, [projectId, onMessage, onSlideUpdate, onWorkflowUpdate, onError, autoReconnect, reconnectInterval])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected')
      wsRef.current = null
    }

    setIsConnected(false)
    setIsConnecting(false)
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
      return true
    }
    console.warn('WebSocket not connected, cannot send message')
    return false
  }, [])

  // Specific action methods
  const generateSlide = useCallback((slideNumber: number) => {
    return sendMessage({
      type: 'generate_slide',
      slide_number: slideNumber
    })
  }, [sendMessage])

  const editSlide = useCallback((slideId: string, request: any) => {
    return sendMessage({
      type: 'edit_slide',
      slide_id: slideId,
      request
    })
  }, [sendMessage])

  const approveSlide = useCallback((slideId: string) => {
    return sendMessage({
      type: 'approve_slide',
      slide_id: slideId
    })
  }, [sendMessage])

  // Connect on mount
  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  // Ping to keep connection alive
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000) // Ping every 30 seconds

    return () => clearInterval(pingInterval)
  }, [])

  return {
    isConnected,
    isConnecting,
    lastMessage,
    sendMessage,
    generateSlide,
    editSlide,
    approveSlide,
    reconnect: connect,
    disconnect
  }
}