import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'

export default function ChatWindow({ messages, isLoading, isDark }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className={`flex-1 overflow-y-auto chat-scroll px-4 py-4 space-y-4
      ${isDark ? 'bg-gray-950' : 'bg-gray-50'}`}>
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} isDark={isDark} />
      ))}

      {/* Typing indicator */}
      {isLoading && (
        <div className="flex gap-3 msg-enter">
          <div className={`w-8 h-8 rounded-full border flex items-center justify-center
            text-base shrink-0
            ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-brand-100 border-brand-200'}`}>
            🤖
          </div>
          <div className={`border shadow-sm rounded-2xl rounded-tl-sm px-4 py-3
            ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-100'}`}>
            <div className="flex gap-1 items-center h-4">
              <div className={`w-2 h-2 rounded-full typing-dot
                ${isDark ? 'bg-gray-500' : 'bg-gray-400'}`} />
              <div className={`w-2 h-2 rounded-full typing-dot
                ${isDark ? 'bg-gray-500' : 'bg-gray-400'}`} />
              <div className={`w-2 h-2 rounded-full typing-dot
                ${isDark ? 'bg-gray-500' : 'bg-gray-400'}`} />
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}