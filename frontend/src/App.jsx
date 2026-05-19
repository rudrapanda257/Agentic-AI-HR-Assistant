import { useState } from 'react'
import ChatWindow from './components/ChatWindow'
import { useChat } from './hooks/useChat'

/**
 * App — root component. Renders the full HR chat UI.
 *
 * Layout:
 *   ┌─────────────────────────────┐
 *   │ Topbar (logo, session info) │
 *   ├─────────────────────────────┤
 *   │ Sidebar (quick questions)   │
 *   │                             │
 *   │ ChatWindow (messages)       │
 *   │                             │
 *   │ InputBar (text + send)      │
 *   └─────────────────────────────┘
 */

const QUICK_QUESTIONS = [
  { label: '🌴 Leave balance', text: 'How many casual leaves do I get per year?' },
  { label: '🏠 WFH policy', text: 'What is the work from home policy?' },
  { label: '📅 Schedule meeting', text: 'Schedule a 30-minute sync with my manager tomorrow at 10am' },
  { label: '✉️ WFH email', text: 'Draft an email to my manager requesting WFH on Friday' },
  { label: '💰 Salary structure', text: 'What does our salary structure look like?' },
  { label: '🩺 Medical benefits', text: 'What medical insurance benefits do we have?' },
]

export default function App() {
  const { messages, isLoading, sessionId, sendMessage, clearChat, error } = useChat()
  const [inputText, setInputText] = useState('')

  const handleSend = async () => {
    const text = inputText.trim()
    if (!text || isLoading) return
    setInputText('')
    await sendMessage(text)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleQuickQuestion = (text) => {
    setInputText('')
    sendMessage(text)
  }

  return (
    <div className="flex w-full h-screen bg-gray-50">

      {/* ── Sidebar ────────────────────────────────────────────────── */}
      <aside className="w-64 shrink-0 bg-white border-r border-gray-100 flex flex-col hidden md:flex">
        {/* Logo */}
        <div className="px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-brand-700 rounded-lg flex items-center justify-center text-white text-sm font-bold">
              HR
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">HR Assistant</p>
              <p className="text-xs text-gray-400">Powered by Gemini</p>
            </div>
          </div>
        </div>

        {/* Quick questions */}
        <div className="flex-1 px-3 py-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-2 mb-2">
            Quick questions
          </p>
          <div className="space-y-1">
            {QUICK_QUESTIONS.map((q) => (
              <button
                key={q.label}
                onClick={() => handleQuickQuestion(q.text)}
                disabled={isLoading}
                className="w-full text-left text-sm text-gray-700 px-3 py-2 rounded-lg 
                  hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {q.label}
              </button>
            ))}
          </div>
        </div>

        {/* Session info + clear */}
        <div className="px-4 py-3 border-t border-gray-100">
          <p className="text-xs text-gray-400 truncate mb-2">
            Session: {sessionId.slice(0, 8)}…
          </p>
          <button
            onClick={clearChat}
            className="w-full text-xs text-gray-500 hover:text-red-500 py-1.5 rounded-lg
              hover:bg-red-50 transition-colors"
          >
            🗑 Clear chat
          </button>
        </div>
      </aside>

      {/* ── Main chat area ─────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0">

        {/* Topbar */}
        <header className="bg-white border-b border-gray-100 px-4 py-3 flex items-center gap-3 shrink-0">
          <div className="w-8 h-8 bg-brand-700 rounded-full flex items-center justify-center text-white text-xs font-bold md:hidden">
            HR
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900">HR Assistant</p>
            <p className="text-xs text-gray-400">
              3 agents: Policy RAG · Calendar · Email
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-xs text-gray-500">Online</span>
          </div>
        </header>

        {/* Agent legend */}
        <div className="bg-gray-50 border-b border-gray-100 px-4 py-2 flex gap-4 overflow-x-auto shrink-0">
          <span className="text-xs text-gray-400 shrink-0">Agents:</span>
          <LegendItem color="bg-emerald-400" label="📄 Policy RAG" />
          <LegendItem color="bg-blue-400" label="📅 Calendar" />
          <LegendItem color="bg-amber-400" label="✉️ Email" />
        </div>

        {/* Messages */}
        <ChatWindow messages={messages} isLoading={isLoading} />

        {/* Error banner */}
        {error && (
          <div className="mx-4 mb-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
            {error}
          </div>
        )}

        {/* Input bar */}
        <div className="bg-white border-t border-gray-100 px-4 py-3 shrink-0">
          <div className="flex gap-2 items-end">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder="Ask about policies, schedule a meeting, or draft an email…"
              rows={1}
              className="flex-1 resize-none border border-gray-200 rounded-xl px-4 py-2.5 text-sm 
                text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 
                focus:ring-brand-500 focus:border-transparent transition-shadow
                disabled:bg-gray-50 disabled:cursor-not-allowed"
              style={{ maxHeight: '120px' }}
              onInput={(e) => {
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
              }}
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !inputText.trim()}
              className="w-10 h-10 bg-brand-700 hover:bg-brand-600 disabled:bg-gray-200 
                disabled:cursor-not-allowed text-white rounded-xl flex items-center justify-center 
                transition-colors shrink-0"
              aria-label="Send message"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M22 2L11 13M22 2L15 22 11 13 2 9l20-7z" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1.5 pl-1">
            Press Enter to send · Shift+Enter for new line
          </p>
        </div>
      </main>
    </div>
  )
}

function LegendItem({ color, label }) {
  return (
    <div className="flex items-center gap-1.5 shrink-0">
      <span className={`w-2 h-2 rounded-full ${color}`} />
      <span className="text-xs text-gray-500">{label}</span>
    </div>
  )
}