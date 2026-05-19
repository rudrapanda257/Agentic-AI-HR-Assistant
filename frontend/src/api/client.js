import axios from 'axios'

// All requests go to /api/* which Vite proxies to http://localhost:8000/*
const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,  // 60s — LLM calls can be slow
})

export const sendChatMessage = (sessionId, message) =>
  client.post('/chat', { session_id: sessionId, message })

export const getChatHistory = (sessionId) =>
  client.get(`/history/${sessionId}`)

export const clearChatHistory = (sessionId) =>
  client.delete(`/history/${sessionId}`)

export const confirmSendEmail = (to, subject, body) =>
  client.post('/confirm-send-email', { to, subject, body })

export const confirmBookEvent = (eventData) =>
  client.post('/confirm-book-event', eventData)

export default client