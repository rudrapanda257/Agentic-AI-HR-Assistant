import AgentBadge from './AgentBadge'
import CalendarCard from './CalendarCard'
import EmailCard from './EmailCard'

export default function MessageBubble({ message, isDark }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end msg-enter">
        <div className="max-w-[75%]">
          <div className="bg-brand-700 text-white rounded-2xl rounded-br-sm px-4 py-2.5 text-sm leading-relaxed shadow-sm">
            {message.content}
          </div>
          <p className={`text-right text-xs mt-1 pr-1
            ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>
            {formatTime(message.timestamp)}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3 msg-enter">
      <div className={`w-8 h-8 rounded-full border flex items-center justify-center
        text-base shrink-0 mt-0.5
        ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-brand-100 border-brand-200'}`}>
        🤖
      </div>

      <div className="max-w-[80%] min-w-0">
        {message.agent && message.agent !== 'error' && (
          <AgentBadge agent={message.agent} isDark={isDark} />
        )}

        <div className={`border shadow-sm rounded-2xl rounded-tl-sm px-4 py-3
          text-sm leading-relaxed
          ${isDark
            ? 'bg-gray-800 border-gray-700 text-gray-200'
            : 'bg-white border-gray-100 text-gray-800'}`}>
          {message.content.split('\n').map((line, i) => (
            <span key={i}>
              {line}
              {i < message.content.split('\n').length - 1 && <br />}
            </span>
          ))}
        </div>

        {/* Source citation chips */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {message.sources.map((src, i) => (
              <span
                key={i}
                className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border
                  ${isDark
                    ? 'text-gray-400 bg-gray-800 border-gray-700'
                    : 'text-gray-500 bg-gray-100 border-gray-200'}`}
                title={`Relevance score: ${src.score}`}
              >
                <span>📄</span>
                {src.source}
                {src.page && <span className={isDark ? 'text-gray-600' : 'text-gray-400'}>· p.{src.page}</span>}
              </span>
            ))}
          </div>
        )}

        {/* Action cards */}
        {message.action_card?.type === 'calendar' && (
          <CalendarCard card={message.action_card} isDark={isDark} />
        )}
        {message.action_card?.type === 'email' && (
          <EmailCard card={message.action_card} isDark={isDark} />
        )}

        <p className={`text-xs mt-1.5 pl-1
          ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>
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