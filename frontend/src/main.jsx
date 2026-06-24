import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import InterviewRoom from './pages/InterviewRoom.jsx'
import CandidateProfile from './pages/CandidateProfile.jsx'

// Path-based routing (no router lib):
//   /interview/:id  → candidate live interview room
//   /candidate/:id  → HR candidate dossier
//   everything else → the HR app shell
const path = window.location.pathname
const interviewMatch = path.match(/^\/interview\/([^/]+)/)
const candidateMatch = path.match(/^\/candidate\/([^/]+)/)

const screen = interviewMatch
  ? <InterviewRoom interviewId={interviewMatch[1]} />
  : candidateMatch
    ? <CandidateProfile candidateId={candidateMatch[1]} />
    : <App />

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {screen}
  </StrictMode>,
)
