import { useState } from 'react'
import { confirmBookEvent } from '../api/client'

/**
 * CalendarCard — shows event details with Confirm / Edit buttons.
 * Displayed when the Calendar agent creates/deletes an event.
 */
export default function CalendarCard({ card }) {
  const [state, setState] = useState('pending') // pending | confirmed | error

  if (!card) return null

  // ── Delete confirmation ─────────────────────────────────────────────────
  if (card.action === 'delete') {
    return (
      <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50 p-4">
        <p className="text-sm font-medium text-blue-800 flex items-center gap-2">
          <span>🗑️</span> Event cancelled
        </p>
        <p className="text-xs text-blue-600 mt-1">Event ID: {card.event_id}</p>
      </div>
    )
  }

  // ── Create confirmation ─────────────────────────────────────────────────
  const handleConfirm = async () => {
    try {
      await confirmBookEvent(card)
      setState('confirmed')
    } catch {
      setState('error')
    }
  }

  const formatTime = (time24) => {
    if (!time24) return ''
    const [h, m] = time24.split(':').map(Number)
    const period = h >= 12 ? 'PM' : 'AM'
    const hour = h % 12 || 12
    return `${hour}:${m.toString().padStart(2, '0')} ${period}`
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    try {
      return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-IN', {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
      })
    } catch {
      return dateStr
    }
  }

  if (state === 'confirmed') {
    return (
      <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <p className="text-sm font-semibold text-emerald-700 flex items-center gap-2">
          <span>✅</span> Meeting booked!
        </p>
        <p className="text-xs text-emerald-600 mt-1">
          {card.title} on {formatDate(card.date)} at {formatTime(card.start_time)}
        </p>
      </div>
    )
  }

  return (
    <div className="mt-3 rounded-xl border border-blue-200 bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <div className="bg-blue-50 px-4 py-2.5 flex items-center gap-2 border-b border-blue-100">
        <span className="text-base">📅</span>
        <span className="text-sm font-semibold text-blue-800">Meeting details</span>
        {card.success && (
          <span className="ml-auto text-xs text-emerald-600 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
            Created in Calendar
          </span>
        )}
      </div>

      {/* Details */}
      <div className="px-4 py-3 space-y-2">
        <Row label="Title" value={card.title} />
        <Row label="Date" value={formatDate(card.date)} />
        <Row label="Time" value={`${formatTime(card.start_time)} · ${card.duration_minutes} min`} />
        {card.attendee_email && <Row label="Invite" value={card.attendee_email} />}
      </div>

      {/* Actions */}
      {state === 'pending' && !card.success && (
        <div className="px-4 pb-3 flex gap-2">
          <button
            onClick={handleConfirm}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 
              text-white text-xs font-medium rounded-lg transition-colors"
          >
            ✓ Confirm
          </button>
          <button
            className="px-4 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 
              hover:bg-gray-200 rounded-lg transition-colors"
          >
            Edit
          </button>
        </div>
      )}

      {state === 'error' && (
        <p className="px-4 pb-3 text-xs text-red-600">
          Failed to confirm. Please try again.
        </p>
      )}
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-900 font-medium text-right max-w-[60%]">{value}</span>
    </div>
  )
}