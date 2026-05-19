/**
 * AgentBadge — small colored pill showing which agent handled the request.
 * Policy = green, Calendar = blue, Email = amber, Error = red.
 */
const AGENT_CONFIG = {
  policy: {
    label: 'Policy RAG',
    icon: '📄',
    classes: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  },
  calendar: {
    label: 'Calendar',
    icon: '📅',
    classes: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  email: {
    label: 'Email',
    icon: '✉️',
    classes: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  error: {
    label: 'Error',
    icon: '⚠️',
    classes: 'bg-red-50 text-red-700 border-red-200',
  },
}

export default function AgentBadge({ agent }) {
  const config = AGENT_CONFIG[agent] || AGENT_CONFIG.policy
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 
        rounded-full border mb-1.5 ${config.classes}`}
    >
      <span>{config.icon}</span>
      {config.label}
    </span>
  )
}