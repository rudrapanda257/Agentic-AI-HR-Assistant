import { useState, useCallback, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { sendChatMessage, clearChatHistory } from '../api/client'

/**
 * useChat — manages all chat state.
 *
 * Returns:
 *   messages      → array of message objects to render
 *   isLoading     → true while waiting for agent response
 *   sessionId     → current session UUID
 *   sendMessage   → call with a string to send a message
 *   clearChat     → reset the conversation
 *   error         → error message string or null
 */
export function useChat() {
  const [sessionId] = useState(() => uuidv4())
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hi! I'm your HR assistant. I can answer policy questions, schedule meetings on your calendar, or help you draft and send emails. What do you need today?",
      agent: 'policy',
      sources: [],
      action_card: null,
      timestamp: new Date().toISOString(),
    },
  ])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const abortRef = useRef(null)

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || isLoading) return

    const CONFIRM_WORDS = ['create', 'send', 'confirm', 'yes', 'ok', 'book']
if (CONFIRM_WORDS.includes(text.trim().toLowerCase())) {
  setMessages(prev => [...prev, {
    id: uuidv4(), role: 'user', content: text.trim(),
    agent: '', sources: [], action_card: null,
    timestamp: new Date().toISOString(),
  }, {
    id: uuidv4(), role: 'assistant',
    content: '👆 Please use the **Create** or **Send** button in the card above — don\'t type it in the chat.',
    agent: 'policy', sources: [], action_card: null,
    timestamp: new Date().toISOString(),
  }])
  return
}

    setError(null)

    // Add user message immediately
    const userMsg = {
      id: uuidv4(),
      role: 'user',
      content: text.trim(),
      agent: '',
      sources: [],
      action_card: null,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)

    try {
      const response = await sendChatMessage(sessionId, text.trim())
      const data = response.data

      const assistantMsg = {
        id: uuidv4(),
        role: 'assistant',
        content: data.answer,
        agent: data.agent,
        intent: data.intent,
        sources: data.sources || [],
        action_card: data.action_card || null,
        timestamp: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      const errMsg = err.response?.data?.detail || err.message || 'Something went wrong'
      setError(errMsg)

      // Show error as a message in chat too
      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          role: 'assistant',
          content: `Sorry, I ran into an issue: ${errMsg}. Please try again.`,
          agent: 'error',
          sources: [],
          action_card: null,
          timestamp: new Date().toISOString(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }, [sessionId, isLoading])

  const clearChat = useCallback(async () => {
    await clearChatHistory(sessionId)
    setMessages([
      {
        id: uuidv4(),
        role: 'assistant',
        content: "Chat cleared! How can I help you?",
        agent: 'policy',
        sources: [],
        action_card: null,
        timestamp: new Date().toISOString(),
      },
    ])
    setError(null)
  }, [sessionId])

  return { messages, isLoading, sessionId, sendMessage, clearChat, error }
}