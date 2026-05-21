import { useState, useEffect, createContext, useContext } from 'react'

const DarkModeContext = createContext(null)

export function DarkModeProvider({ children }) {
  const [isDark, setIsDark] = useState(() => {
    // Read from localStorage if available, default to false
    try {
      return localStorage.getItem('hr-dark-mode') === 'true'
    } catch {
      return false
    }
  })

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    try {
      localStorage.setItem('hr-dark-mode', String(isDark))
    } catch { /* ignore */ }
  }, [isDark])

  const toggle = () => setIsDark(prev => !prev)

  return (
    <DarkModeContext.Provider value={{ isDark, toggle }}>
      {children}
    </DarkModeContext.Provider>
  )
}

export function useDarkMode() {
  const ctx = useContext(DarkModeContext)
  if (!ctx) throw new Error('useDarkMode must be used inside DarkModeProvider')
  return ctx
}