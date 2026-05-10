import { useState } from 'react'
import BirthForm from './components/BirthForm.jsx'
import ChatInterface from './components/ChatInterface.jsx'
import Stars from './components/Stars.jsx'

export default function App() {
  const [session, setSession] = useState(null)
  // session: { session_id, name, ascendant, sun_sign, moon_sign, moon_nakshatra, ... }

  function handleChartReady(sessionData) {
    setSession(sessionData)
  }

  function handleReset() {
    setSession(null)
  }

  return (
    <>
      <Stars />
      {session
        ? <ChatInterface session={session} onReset={handleReset} />
        : <BirthForm onChartReady={handleChartReady} />
      }
    </>
  )
}
