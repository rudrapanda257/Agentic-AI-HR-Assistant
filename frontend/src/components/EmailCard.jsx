import { useState } from 'react'
import { confirmSendEmail } from '../api/client'

/**
 * EmailCard — shows email draft preview.
 * User must click "Send email" to actually send.
 * Until then, nothing goes to Gmail.
 */
export default function EmailCard({ card }) {
  const [state, setState] = useState('draft')   // draft | sending | sent | error
  const [isExpanded, setIsExpanded] = useState(true)

  if (!card) return null

  // Already sent
  if (card.sent) {
    return (
      <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <p className="text-sm font-semibold text-amber-800 flex items-center gap-2">
          <span>✉️</span> {card.success ? 'Email sent!' : 'Send failed'}
        </p>
        <p className="text-xs text-amber-600 mt-1">{card.message}</p>
      </div>
    )
  }

  const handleSend = async () => {
    setState('sending')
    try {
      await confirmSendEmail(card.to, card.subject, card.body)
      setState('sent')
    } catch (err) {
      setState('error')
    }
  }

  if (state === 'sent') {
    return (
      <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <p className="text-sm font-semibold text-emerald-700 flex items-center gap-2">
          <span>✅</span> Email sent successfully!
        </p>
        <p className="text-xs text-emerald-600 mt-1">To: {card.to}</p>
      </div>
    )
  }

  return (
    <div className="mt-3 rounded-xl border border-amber-200 bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <div
        className="bg-amber-50 px-4 py-2.5 flex items-center gap-2 border-b border-amber-100 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="text-base">✉️</span>
        <span className="text-sm font-semibold text-amber-800">Email draft</span>
        <span className="ml-auto text-amber-400 text-xs">{isExpanded ? '▲' : '▼'}</span>
      </div>

      {isExpanded && (
        <>
          {/* Email metadata */}
          <div className="px-4 pt-3 pb-1 space-y-1.5 border-b border-gray-100">
            <MetaRow label="To" value={card.to} />
            <MetaRow label="Subject" value={card.subject} />
          </div>

          {/* Email body */}
          <div className="px-4 py-3">
            <p className="text-xs text-gray-500 mb-1.5 uppercase tracking-wide font-medium">Body</p>
            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed bg-gray-50 
              rounded-lg p-3 border border-gray-100">
              {card.body}
            </p>
          </div>

          {/* Actions */}
          <div className="px-4 pb-4 flex gap-2">
            {state === 'draft' && (
              <>
                <button
                  onClick={handleSend}
                  className="flex items-center gap-1.5 px-4 py-1.5 bg-amber-600 hover:bg-amber-700
                    text-white text-xs font-medium rounded-lg transition-colors"
                >
                  ✈ Send email
                </button>
                <button
                  className="px-4 py-1.5 text-xs font-medium text-gray-600 bg-gray-100
                    hover:bg-gray-200 rounded-lg transition-colors"
                >
                  Edit draft
                </button>
              </>
            )}
            {state === 'sending' && (
              <div className="flex items-center gap-2 text-xs text-amber-600">
                <div className="w-3 h-3 border-2 border-amber-400 border-t-transparent 
                  rounded-full animate-spin" />
                Sending...
              </div>
            )}
            {state === 'error' && (
              <>
                <p className="text-xs text-red-600 self-center">Send failed. Try again?</p>
                <button
                  onClick={handleSend}
                  className="px-3 py-1.5 text-xs text-red-600 border border-red-200 
                    rounded-lg hover:bg-red-50 transition-colors"
                >
                  Retry
                </button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function MetaRow({ label, value }) {
  return (
    <div className="flex gap-3 text-sm">
      <span className="text-gray-400 w-14 shrink-0">{label}</span>
      <span className="text-gray-900">{value || '—'}</span>
    </div>
  )
}