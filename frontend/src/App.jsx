import { useState, useEffect } from 'react'
import { Analytics } from '@vercel/analytics/react'
import BirthForm from './components/BirthForm.jsx'
import ChatInterface from './components/ChatInterface.jsx'
import KnowTheCreator from './components/KnowTheCreator.jsx'
import Navbar from './components/Navbar.jsx'
import Stars from './components/Stars.jsx'

export default function App() {
  const [session, setSession] = useState(null)
  const [page, setPage]       = useState('home') // 'home' | 'creator'
  const [darkMode, setDarkMode] = useState(true)  // default: dark

  // Apply theme to <html>
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  function handleChartReady(sessionData) {
    setSession(sessionData)
    setPage('home')
  }

  function handleReset() {
    setSession(null)
    setPage('home')
  }

  function handleNavigate(dest) {
    if (dest === 'home') {
      setPage('home')
    } else {
      setPage(dest)
    }
  }

  return (
    <>
      <Stars />
      <Navbar
        page={page}
        onNavigate={handleNavigate}
        darkMode={darkMode}
        onToggleDark={() => setDarkMode(d => !d)}
      />

      {page === 'creator' ? (
        <KnowTheCreator />
      ) : session ? (
        <ChatInterface session={session} onReset={handleReset} />
      ) : (
        <BirthForm onChartReady={handleChartReady} />
      )}

      <Analytics />
    </>
  )
}
