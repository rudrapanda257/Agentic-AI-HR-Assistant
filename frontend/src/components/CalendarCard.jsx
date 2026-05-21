import { useState } from 'react'
import { confirmBookEvent } from '../api/client'

/**
 * CalendarCard — Full edit form + Create button.
 * 
 * States:
 *   editing  → user can modify title, date, time, duration, invite email
 *   creating → spinner while API call in progress
 *   created  → success confirmation
 *   error    → shows error, retry option
 */
export default function CalendarCard({ card, isDark }) {
  const [state, setState] = useState('editing') // editing | creating | created | error
  const [errorMsg, setErrorMsg] = useState('')

  // Editable fields
  const [title, setTitle]             = useState(card.title || '')
  const [date, setDate]               = useState(card.date || '')
  const [startTime, setStartTime]     = useState(card.start_time || '')
  const [duration, setDuration]       = useState(card.duration_minutes || 30)
  const [attendeeEmail, setAttendeeEmail] = useState(card.attendee_email || '')
  const [description, setDescription]    = useState(card.description || '')

  if (!card) return null

  // ── Delete card ─────────────────────────────────────────────────────────
  if (card.action === 'delete') {
    return (
      <div className={`mt-3 rounded-xl border p-4
        ${isDark ? 'border-blue-900 bg-blue-950' : 'border-blue-100 bg-blue-50'}`}>
        <p className={`text-sm font-medium flex items-center gap-2
          ${isDark ? 'text-blue-300' : 'text-blue-800'}`}>
          <span>🗑️</span> Event cancelled
        </p>
        <p className={`text-xs mt-1 ${isDark ? 'text-blue-500' : 'text-blue-600'}`}>
          Event ID: {card.event_id}
        </p>
      </div>
    )
  }

  // ── Success state ────────────────────────────────────────────────────────
  if (state === 'created') {
    return (
      <div className={`mt-3 rounded-xl border p-4
        ${isDark ? 'border-emerald-900 bg-emerald-950' : 'border-emerald-200 bg-emerald-50'}`}>
        <p className={`text-sm font-semibold flex items-center gap-2
          ${isDark ? 'text-emerald-400' : 'text-emerald-700'}`}>
          <span>✅</span> Meeting created in Google Calendar!
        </p>
        <p className={`text-xs mt-1 ${isDark ? 'text-emerald-600' : 'text-emerald-600'}`}>
          {title} · {formatDate(date)} · {formatTime(startTime)} · {duration} min
          {attendeeEmail && ` · Invite sent to ${attendeeEmail}`}
        </p>
      </div>
    )
  }

  const handleCreate = async () => {
    if (!title.trim() || !date || !startTime) {
      setErrorMsg('Please fill in Title, Date, and Time.')
      return
    }
    setState('creating')
    setErrorMsg('')
    try {
      await confirmBookEvent({
        title: title.trim(),
        date,
        start_time: startTime,
        duration_minutes: Number(duration),
        attendee_email: attendeeEmail.trim() || null,
        description: description.trim(),
      })
      setState('created')
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to create event'
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
      ${isDark ? 'border-blue-900 bg-gray-800' : 'border-blue-200 bg-white'}`}>

      {/* Header */}
      <div className={`px-4 py-2.5 flex items-center gap-2 border-b
        ${isDark ? 'bg-blue-950 border-blue-900' : 'bg-blue-50 border-blue-100'}`}>
        <span className="text-base">📅</span>
        <span className={`text-sm font-semibold
          ${isDark ? 'text-blue-300' : 'text-blue-800'}`}>
          Review & Create Calendar Event
        </span>
      </div>

      {/* Edit form */}
      <div className="px-4 py-3 space-y-3">
        {/* Title */}
        <div>
          <label className={labelClass}>Event Title *</label>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g. 1:1 with Manager"
            className={inputClass}
            disabled={state === 'creating'}
          />
        </div>

        {/* Date + Time row */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className={labelClass}>Date *</label>
            <input
              type="date"
              value={date}
              onChange={e => setDate(e.target.value)}
              className={inputClass}
              disabled={state === 'creating'}
            />
          </div>
          <div>
            <label className={labelClass}>Start Time *</label>
            <input
              type="time"
              value={startTime}
              onChange={e => setStartTime(e.target.value)}
              className={inputClass}
              disabled={state === 'creating'}
            />
          </div>
        </div>

        {/* Duration */}
        <div>
          <label className={labelClass}>Duration (minutes)</label>
          <select
            value={duration}
            onChange={e => setDuration(Number(e.target.value))}
            className={inputClass}
            disabled={state === 'creating'}
          >
            {[15, 30, 45, 60, 90, 120].map(d => (
              <option key={d} value={d}>{d} min{d >= 60 ? ` (${d/60}h)` : ''}</option>
            ))}
          </select>
        </div>

        {/* Invite email */}
        <div>
          <label className={labelClass}>Invite (email — optional)</label>
          <input
            type="email"
            value={attendeeEmail}
            onChange={e => setAttendeeEmail(e.target.value)}
            placeholder="colleague@company.com"
            className={inputClass}
            disabled={state === 'creating'}
          />
        </div>

        {/* Description */}
        <div>
          <label className={labelClass}>Description (optional)</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Meeting agenda or notes…"
            rows={2}
            className={`${inputClass} resize-none`}
            disabled={state === 'creating'}
          />
        </div>

        {/* Error */}
        {errorMsg && (
          <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {errorMsg}
          </p>
        )}
      </div>

      {/* Action buttons */}
      <div className={`px-4 pb-4 flex gap-2 border-t pt-3
        ${isDark ? 'border-gray-700' : 'border-gray-100'}`}>
        <button
          onClick={handleCreate}
          disabled={state === 'creating'}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700
            disabled:bg-blue-400 disabled:cursor-not-allowed text-white text-xs font-semibold
            rounded-lg transition-colors"
        >
          {state === 'creating' ? (
            <>
              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Creating…
            </>
          ) : (
            <>📅 Create in Google Calendar</>
          )}
        </button>
        <button
          onClick={() => {
            setTitle(''); setDate(''); setStartTime('')
            setDuration(30); setAttendeeEmail(''); setDescription('')
          }}
          disabled={state === 'creating'}
          className={`px-4 py-2 text-xs font-medium rounded-lg transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed
            ${isDark
              ? 'text-gray-400 bg-gray-700 hover:bg-gray-600'
              : 'text-gray-600 bg-gray-100 hover:bg-gray-200'}`}
        >
          Clear
        </button>
      </div>
    </div>
  )
}

function formatTime(time24) {
  if (!time24) return ''
  const [h, m] = time24.split(':').map(Number)
  const period = h >= 12 ? 'PM' : 'AM'
  const hour = h % 12 || 12
  return `${hour}:${String(m).padStart(2, '0')} ${period}`
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  try {
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-IN', {
      weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
    })
  } catch {
    return dateStr
  }
}