import { useState, useEffect } from 'react'
import BirthForm      from './components/BirthForm.jsx'
import ChatInterface  from './components/ChatInterface.jsx'
import KnowTheCreator from './components/KnowTheCreator.jsx'
import Navbar         from './components/Navbar.jsx'
import Stars          from './components/Stars.jsx'
import ProfilePanel, { getActiveSession } from './components/ProfilePanel.jsx'

export default function App() {
  const [session,          setSession]          = useState(null)
  const [page,             setPage]             = useState('home')
  const [darkMode,         setDarkMode]         = useState(true)
  const [profilePanelOpen, setProfilePanelOpen] = useState(false)
  const [chartSaved,       setChartSaved]       = useState(false)
  const [profileUsername,  setProfileUsername]  = useState(null)

  // Apply theme to <html>
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  // Restore logged-in username from sessionStorage on mount
  useEffect(() => {
    const active = getActiveSession()
    if (active?.username) setProfileUsername(active.username)
  }, [])

  function handleChartReady(sessionData) {
    setSession(sessionData)
    setPage('home')
    setChartSaved(false)      // new chart = unsaved
    // Open profile panel after a short delay so the user lands on the
    // chat page first, then sees the prompt
    // (The pulsing CTA in ChatInterface + pulsing Navbar button handle this)
  }

  function handleReset() {
    setSession(null)
    setPage('home')
    setChartSaved(false)
    setProfilePanelOpen(false)
  }

  function handleNavigate(dest) {
    setPage(dest === 'home' ? 'home' : dest)
    setProfilePanelOpen(false)
  }

  function handleOpenProfile() {
    setProfilePanelOpen(true)
  }

  function handleCloseProfile() {
    setProfilePanelOpen(false)
  }

  function handleChartSaved() {
    setChartSaved(true)
    // keep panel open so user can see the saved chart
  }

  // Called from ProfilePanel when user loads a saved chart
  function handleLoadChart(savedSession) {
    setSession(savedSession)
    setPage('home')
    setChartSaved(true)       // it's a restored chart — already "saved"
    setProfilePanelOpen(false)
  }

  // Sync profile username after login/logout inside the panel
  // We poll sessionStorage lightly via a small helper
  function handleProfileUsernameSync() {
    const active = getActiveSession()
    setProfileUsername(active?.username || null)
  }

  // The Navbar button pulses when a chart is active but not yet saved
  const profilePulsing = !!session && !chartSaved

  return (
    <>
      <Stars />

      <Navbar
        page={page}
        onNavigate={handleNavigate}
        darkMode={darkMode}
        onToggleDark={() => setDarkMode(d => !d)}
        profileUsername={profileUsername}
        onOpenProfile={handleOpenProfile}
        profilePulsing={profilePulsing}
      />

      {page === 'creator' ? (
        <KnowTheCreator />
      ) : session ? (
        <ChatInterface
          session={session}
          onReset={handleReset}
          chartSaved={chartSaved}
          onOpenProfile={handleOpenProfile}
        />
      ) : (
        <BirthForm onChartReady={handleChartReady} />
      )}

      {/* Profile panel — rendered at App level so it overlays everything */}
      {profilePanelOpen && (
        <ProfilePanel
          onClose={() => {
            handleCloseProfile()
            handleProfileUsernameSync()
          }}
          currentSession={session}
          onChartSaved={handleChartSaved}
          onLoadChart={handleLoadChart}
          suggestedName={session?.name || ''}
        />
      )}
    </>
  )
}
