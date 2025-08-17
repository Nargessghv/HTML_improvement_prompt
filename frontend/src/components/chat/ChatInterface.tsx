'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Bot, User, Sparkles } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  suggestions?: string[]
}

interface PresentationOutline {
  title: string
  topic: string
  target_audience?: string
  objectives: string[]
  key_themes: string[]
  estimated_duration?: number
  style_preferences: Record<string, unknown>
  slides: Array<{
    slide_number: number
    title: string
    is_html: boolean
    is_image: boolean
    key_points: string[]
  }>
}

interface ChatInterfaceProps {
  sessionId?: string
  projectId: string
  initialTopic?: string
  onOutlineGenerated?: (outline: PresentationOutline, fullOutline?: PresentationOutline, sessionId?: string) => void
  onSessionCreated?: (sessionId: string) => void
  className?: string
}

export function ChatInterface({ 
  sessionId: initialSessionId,
  projectId, 
  initialTopic,
  onOutlineGenerated,
  onSessionCreated,
  className 
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | undefined>(initialSessionId)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [isGeneratingOutline, setIsGeneratingOutline] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { supabase } = useSupabaseAuth()

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }, [messages])

  // Start chat session on mount if topic provided
  useEffect(() => {
    if (initialTopic && !sessionId) {
      startChatSession(initialTopic)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTopic])

  const startChatSession = async (topic: string) => {
    try {
      setIsLoading(true)
      
      // Get the current session for auth token
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        throw new Error('No authentication session')
      }
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/chat/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          project_id: projectId,
          initial_topic: topic
        })
      })

      if (!response.ok) throw new Error('Failed to start chat session')

      const data = await response.json()
      
      // Set session ID from response
      if (data.session_id) {
        setSessionId(data.session_id)
        if (onSessionCreated) {
          onSessionCreated(data.session_id)
        }
      }

      // Add initial messages
      const timestamp = new Date().toISOString()
      setMessages([
        {
          id: crypto.randomUUID(),
          role: 'user',
          content: topic,
          timestamp
        },
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.response,
          timestamp: new Date().toISOString(),
          suggestions: data.suggestions
        }
      ])
      setSuggestions(data.suggestions || [])
    } catch (error) {
      console.error('Error starting chat:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || isLoading) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      // Get the current session for auth token
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        throw new Error('No authentication session')
      }
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMessage.content
        })
      })

      if (!response.ok) throw new Error('Failed to send message')

      const data = await response.json()

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        suggestions: data.suggestions
      }

      setMessages(prev => [...prev, assistantMessage])
      setSuggestions(data.suggestions || [])

      // If outline was generated, notify parent
      if (data.outline && onOutlineGenerated) {
        onOutlineGenerated(data.outline, data.full_outline, sessionId)
      }
    } catch (error) {
      console.error('Error sending message:', error)
      // Add error message
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const generateOutline = async () => {
    if (!sessionId || isGeneratingOutline) return

    setIsGeneratingOutline(true)

    try {
      // Get the current session for auth token
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        throw new Error('No authentication session')
      }
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`/api/chat/${sessionId}/generate-outline`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        }
      })

      if (!response.ok) throw new Error('Failed to generate outline')

      const data = await response.json()

      // console.log('🔍 Generate outline response:', data)
      // console.log('🔍 Has outline:', !!data.outline) 
      // console.log('🔍 Outline data:', data.outline)

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        suggestions: data.suggestions
      }

      setMessages(prev => [...prev, assistantMessage])
      setSuggestions(data.suggestions || [])

      // If outline was generated, notify parent
      if (data.outline && onOutlineGenerated) {
        // console.log('🔍 Calling onOutlineGenerated with:', data.outline)
        // console.log('🔍 Full outline:', data.full_outline)
        onOutlineGenerated(data.outline, data.full_outline, sessionId)
      } else {
        // console.log('🔍 No outline found in response or no onOutlineGenerated callback')
      }
    } catch (error) {
      console.error('Error generating outline:', error)
      // Add error message
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Sorry, I encountered an error while generating the outline. Please try again.',
        timestamp: new Date().toISOString()
      }])
    } finally {
      setIsGeneratingOutline(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion)
    textareaRef.current?.focus()
  }

  return (
    <Card className={cn("flex flex-col h-full", className)}>
      <div className="border-b p-4">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Presentation Planning Assistant</h3>
          <Badge variant="secondary" className="ml-auto">
            <Sparkles className="w-3 h-3 mr-1" />
            AI Powered
          </Badge>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4 h-0" ref={scrollAreaRef}>
        <div className="space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <Bot className="w-12 h-12 mx-auto mb-4 text-muted-foreground/50" />
              <p className="text-sm">
                Start planning your presentation by describing your topic and goals.
              </p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex gap-3",
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-primary" />
                </div>
              )}
              
              <div
                className={cn(
                  "max-w-[80%] rounded-lg px-4 py-2",
                  message.role === 'user'
                    ? 'bg-ekona-red text-white'
                    : 'bg-muted'
                )}
              >
                <div className="text-sm prose prose-sm max-w-none dark:prose-invert prose-p:leading-relaxed prose-pre:p-0">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      ul: ({ children }) => <ul className="ml-4 mb-2 list-disc space-y-1">{children}</ul>,
                      ol: ({ children }) => <ol className="ml-4 mb-2 list-decimal space-y-1">{children}</ol>,
                      li: ({ children }) => <li className="text-sm">{children}</li>,
                      h1: ({ children }) => <h1 className="text-lg font-semibold mb-2">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-md font-semibold mb-2">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-sm font-semibold mb-1">{children}</h3>,
                      code: ({ children }) => <code className="bg-muted px-1 py-0.5 rounded text-xs">{children}</code>,
                      pre: ({ children }) => <pre className="bg-muted p-2 rounded text-xs overflow-x-auto">{children}</pre>
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
                {message.suggestions && message.suggestions.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border/50">
                    <p className="text-xs font-medium mb-2 opacity-70">Suggestions:</p>
                    <div className="space-y-1">
                      {message.suggestions.map((suggestion, idx) => (
                        <p key={idx} className="text-xs opacity-90">• {suggestion}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {message.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-ekona-red flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className="bg-muted rounded-lg px-4 py-2">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span className="text-sm">Thinking...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {suggestions.length > 0 && (
        <div className="p-3 border-t bg-muted/50">
          <p className="text-xs font-medium text-muted-foreground mb-2">Quick actions:</p>
          <div className="flex flex-wrap gap-2">
            {suggestions.slice(0, 3).map((suggestion, idx) => (
              <Button
                key={idx}
                variant="outline"
                size="sm"
                className="text-xs"
                onClick={() => handleSuggestionClick(suggestion)}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        </div>
      )}

      <div className="p-4 border-t">
        {/* Generate Outline button - show when we have some conversation */}
        {messages.length >= 2 && sessionId && (
          <div className="mb-3">
            <Button
              onClick={generateOutline}
              disabled={isGeneratingOutline || isLoading}
              variant="outline"
              className="w-full bg-primary/5 hover:bg-primary/10 border-primary/20"
            >
              {isGeneratingOutline ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating Outline...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Generate Presentation Outline
                </>
              )}
            </Button>
          </div>
        )}
        
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="min-h-[60px] resize-none"
            disabled={isLoading || !sessionId}
          />
          <Button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading || !sessionId}
            size="icon"
            className="h-[60px] w-[60px]"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </Card>
  )
}