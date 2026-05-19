import AgentBadge from './AgentBadge'
import CalendarCard from './CalendarCard'
import EmailCard from './EmailCard'

/**
 * MessageBubble — renders one message (user or assistant).
 *
 * Assistant messages show:
 *   - AgentBadge (which agent handled it)
 *   - Text response
 *   - Source citation chips (policy RAG)
 *   - CalendarCard or EmailCard (action confirmation)
 */
export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end msg-enter">
        <div className="max-w-[75%]">
          <div className="bg-brand-700 text-white rounded-2xl rounded-br-sm px-4 py-2.5 text-sm leading-relaxed shadow-sm">
            {message.content}
          </div>
          <p className="text-right text-xs text-gray-400 mt-1 pr-1">
            {formatTime(message.timestamp)}
          </p>
        </div>
      </div>
    )
  }

  // ── Assistant message ───────────────────────────────────────────────────
  return (
    <div className="flex gap-3 msg-enter">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-brand-100 border border-brand-200 flex items-center 
        justify-center text-base shrink-0 mt-0.5">
        🤖
      </div>

      <div className="max-w-[80%] min-w-0">
        {/* Agent badge */}
        {message.agent && message.agent !== 'error' && (
          <AgentBadge agent={message.agent} />
        )}

        {/* Message bubble */}
        <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800 leading-relaxed">
          {/* Render text with basic markdown-style line breaks */}
          {message.content.split('\n').map((line, i) => (
            <span key={i}>
              {line}
              {i < message.content.split('\n').length - 1 && <br />}
            </span>
          ))}
        </div>

        {/* Source citation chips — only for policy agent */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {message.sources.map((src, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 text-xs text-gray-500 bg-gray-100 
                  border border-gray-200 px-2.5 py-1 rounded-full"
                title={`Relevance score: ${src.score}`}
              >
                <span>📄</span>
                {src.source}
                {src.page && <span className="text-gray-400">· p.{src.page}</span>}
              </span>
            ))}
          </div>
        )}

        {/* Action cards — calendar or email */}
        {message.action_card?.type === 'calendar' && (
          <CalendarCard card={message.action_card} />
        )}
        {message.action_card?.type === 'email' && (
          <EmailCard card={message.action_card} />
        )}

        <p className="text-xs text-gray-400 mt-1.5 pl-1">
          {formatTime(message.timestamp)}
        </p>
      </div>
    </div>
  )
}

function formatTime(isoString) {
  if (!isoString) return ''
  try {
    return new Date(isoString).toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit', hour12: true,
    })
  } catch {
    return ''
  }
}