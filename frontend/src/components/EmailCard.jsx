import { useState } from 'react'
import { confirmSendEmail } from '../api/client'

/**
 * EmailCard — inline edit + real Send via Gmail API.
 *
 * States:
 *   editing  → user can edit To, Subject, Body
 *   sending  → spinner while API call
 *   sent     → success
 *   error    → shows error, retry
 */
export default function EmailCard({ card, isDark }) {
  const [state, setState] = useState('editing') // editing | sending | sent | error
  const [errorMsg, setErrorMsg] = useState('')
  const [isExpanded, setIsExpanded] = useState(true)

  // Editable fields (pre-populated from agent draft)
  const [to, setTo]           = useState(card.to || '')
  const [subject, setSubject] = useState(card.subject || '')
  const [body, setBody]       = useState(card.body || '')

  if (!card) return null

  // Already sent (from agent's send_email tool path)
  if (card.sent) {
    return (
      <div className={`mt-3 rounded-xl border p-4
        ${isDark ? 'border-amber-900 bg-amber-950' : 'border-amber-200 bg-amber-50'}`}>
        <p className={`text-sm font-semibold flex items-center gap-2
          ${isDark ? 'text-amber-300' : 'text-amber-800'}`}>
          <span>✉️</span> {card.success ? 'Email sent!' : 'Send failed'}
        </p>
        <p className={`text-xs mt-1 ${isDark ? 'text-amber-600' : 'text-amber-600'}`}>
          {card.message}
        </p>
      </div>
    )
  }

  // Success state
  if (state === 'sent') {
    return (
      <div className={`mt-3 rounded-xl border p-4
        ${isDark ? 'border-emerald-900 bg-emerald-950' : 'border-emerald-200 bg-emerald-50'}`}>
        <p className={`text-sm font-semibold flex items-center gap-2
          ${isDark ? 'text-emerald-400' : 'text-emerald-700'}`}>
          <span>✅</span> Email sent successfully via Gmail!
        </p>
        <p className={`text-xs mt-1 ${isDark ? 'text-emerald-600' : 'text-emerald-600'}`}>
          To: {to} · Subject: {subject}
        </p>
      </div>
    )
  }

  const handleSend = async () => {
    if (!to.trim() || !subject.trim() || !body.trim()) {
      setErrorMsg('Please fill in To, Subject, and Body.')
      return
    }
    setState('sending')
    setErrorMsg('')
    try {
      await confirmSendEmail(to.trim(), subject.trim(), body.trim())
      setState('sent')
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to send email'
      setErrorMsg(msg)
      setState('editing')
    }
  }

  const inputClass = `w-full text-sm rounded-lg px-3 py-2 border focus:outline-none
    focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-shadow
    ${isDark
      ? 'bg-gray-700 border-gray-600 text-gray-100 placeholder-gray-500'
      : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400'}`

  const labelClass = `text-xs font-medium mb-1 block
    ${isDark ? 'text-gray-400' : 'text-gray-500'}`

  return (
    <div className={`mt-3 rounded-xl border overflow-hidden shadow-sm
      ${isDark ? 'border-amber-900 bg-gray-800' : 'border-amber-200 bg-white'}`}>

      {/* Header */}
      <div
        className={`px-4 py-2.5 flex items-center gap-2 border-b cursor-pointer
          ${isDark ? 'bg-amber-950 border-amber-900' : 'bg-amber-50 border-amber-100'}`}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="text-base">✉️</span>
        <span className={`text-sm font-semibold
          ${isDark ? 'text-amber-300' : 'text-amber-800'}`}>
          Email Draft — Edit before sending
        </span>
        <span className={`ml-auto text-xs
          ${isDark ? 'text-amber-700' : 'text-amber-400'}`}>
          {isExpanded ? '▲' : '▼'}
        </span>
      </div>

      {isExpanded && (
        <>
          <div className="px-4 py-3 space-y-3">
            {/* To */}
            <div>
              <label className={labelClass}>To *</label>
              <input
                type="email"
                value={to}
                onChange={e => setTo(e.target.value)}
                placeholder="recipient@example.com"
                className={inputClass}
                disabled={state === 'sending'}
              />
            </div>

            {/* Subject */}
            <div>
              <label className={labelClass}>Subject *</label>
              <input
                type="text"
                value={subject}
                onChange={e => setSubject(e.target.value)}
                placeholder="Email subject"
                className={inputClass}
                disabled={state === 'sending'}
              />
            </div>

            {/* Body */}
            <div>
              <label className={labelClass}>Body *</label>
              <textarea
                value={body}
                onChange={e => setBody(e.target.value)}
                placeholder="Email body…"
                rows={6}
                className={`${inputClass} resize-y min-h-[120px]`}
                disabled={state === 'sending'}
              />
            </div>

            {/* Error */}
            {errorMsg && (
              <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {errorMsg}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className={`px-4 pb-4 flex gap-2 border-t pt-3
            ${isDark ? 'border-gray-700' : 'border-gray-100'}`}>
            <button
              onClick={handleSend}
              disabled={state === 'sending'}
              className="flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700
                disabled:bg-amber-400 disabled:cursor-not-allowed text-white text-xs font-semibold
                rounded-lg transition-colors"
            >
              {state === 'sending' ? (
                <>
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Sending…
                </>
              ) : (
                <>✈️ Send via Gmail</>
              )}
            </button>

            <button
              onClick={() => {
                setTo(card.to || '')
                setSubject(card.subject || '')
                setBody(card.body || '')
                setErrorMsg('')
              }}
              disabled={state === 'sending'}
              className={`px-4 py-2 text-xs font-medium rounded-lg transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
                ${isDark
                  ? 'text-gray-400 bg-gray-700 hover:bg-gray-600'
                  : 'text-gray-600 bg-gray-100 hover:bg-gray-200'}`}
            >
              Reset
            </button>
          </div>
        </>
      )}
    </div>
  )
}