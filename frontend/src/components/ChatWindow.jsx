import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'

/**
 * ChatWindow — scrollable area that renders all messages.
 * Auto-scrolls to bottom on new messages.
 * Shows typing indicator while loading.
 */
export default function ChatWindow({ messages, isLoading }) {
  const bottomRef = useRef(null)

  // Auto-scroll to bottom whenever messages change or loading starts
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="flex-1 overflow-y-auto chat-scroll px-4 py-4 space-y-4">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {/* Typing indicator */}
      {isLoading && (
        <div className="flex gap-3 msg-enter">
          <div className="w-8 h-8 rounded-full bg-brand-100 border border-brand-200 flex items-center justify-center text-base shrink-0">
            🤖
          </div>
          <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-tl-sm px-4 py-3">
            <div className="flex gap-1 items-center h-4">
              <div className="w-2 h-2 rounded-full bg-gray-400 typing-dot" />
              <div className="w-2 h-2 rounded-full bg-gray-400 typing-dot" />
              <div className="w-2 h-2 rounded-full bg-gray-400 typing-dot" />
            </div>
          </div>
        </div>
      )}

      {/* Invisible anchor for auto-scroll */}
      <div ref={bottomRef} />
    </div>
  )
}