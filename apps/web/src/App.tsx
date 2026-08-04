import { Navigate, Route, Routes } from 'react-router-dom'

import { token } from './lib/api'
import { HomePage } from './pages/HomePage'
import { ExercisePage } from './pages/ExercisePage'
import { LandingPage } from './pages/LandingPage'
import { DemoBanner } from './components/DemoBanner'
import { OAuthCallbackPage } from './pages/OAuthCallbackPage'
import { AccountPage } from './pages/AccountPage'
import { AuthPage } from './pages/AuthPage'
import { InstructorPage } from './pages/InstructorPage'
import { PlanPage } from './pages/PlanPage'
import { PortfolioPage } from './pages/PortfolioPage'
import { QuizPage } from './pages/QuizPage'
import { ReflectPage } from './pages/ReflectPage'
import { TopicPage } from './pages/TopicPage'
import { WelcomeChatPage } from './pages/WelcomeChatPage'
import { WelcomePage } from './pages/WelcomePage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  // Presence check only. The API is the authority on whether a token is valid;
  // this just avoids rendering a page that's about to 401.
  if (!token.get()) return <Navigate to="/login" replace />
  // Every signed-in page, so a demo says so wherever you wander to.
  return (
    <>
      <DemoBanner />
      {children}
    </>
  )
}

export function App() {
  return (
    <Routes>
      {/* Public. The landing page manages its own full-bleed layout, so it sits
          outside the padded .app wrapper the signed-in pages use. */}
      <Route path="/" element={<LandingPage />} />

      <Route
        path="/login"
        element={
          <main className="app">
            <AuthPage mode="login" />
          </main>
        }
      />

      <Route
        path="/signup"
        element={
          <main className="app">
            <AuthPage mode="signup" />
          </main>
        }
      />

      {/* Where the API drops the browser after a Google/Microsoft sign-in.
          Public, because the user has no token until this page stores one. */}
      <Route
        path="/auth/callback"
        element={
          <main className="app">
            <OAuthCallbackPage />
          </main>
        }
      />

      {/* Step two of signing up. Behind auth because it writes to the account
          that was just created, and reachable again later from /account. */}
      <Route
        path="/welcome"
        element={
          <RequireAuth>
            <main className="app">
              <WelcomePage />
            </main>
          </RequireAuth>
        }
      />

      <Route
        path="/welcome/chat"
        element={
          <RequireAuth>
            <main className="app">
              <WelcomeChatPage />
            </main>
          </RequireAuth>
        }
      />

      <Route
        path="/account"
        element={
          <RequireAuth>
            <main className="app">
              <AccountPage />
            </main>
          </RequireAuth>
        }
      />

      <Route
        path="/exercises"
        element={
          <RequireAuth>
            <HomePage />
          </RequireAuth>
        }
      />

      <Route
        path="/topic/:topicKey"
        element={
          <RequireAuth>
            <TopicPage />
          </RequireAuth>
        }
      />

      {/* Two paths, one page. The bare /plan is the Read view, so the tab a
        learner lands on and the tab they click back to share an address. */}
      <Route
        path="/exercise/:slug/plan"
        element={
          <RequireAuth>
            <main className="app">
              <PlanPage />
            </main>
          </RequireAuth>
        }
      />

      <Route
        path="/exercise/:slug/plan/:view"
        element={
          <RequireAuth>
            <main className="app">
              <PlanPage />
            </main>
          </RequireAuth>
        }
      />

      <Route
        path="/exercise/:slug/quiz"
        element={
          <RequireAuth>
            <main className="app">
              <QuizPage />
            </main>
          </RequireAuth>
        }
      />

      <Route
        path="/exercise/:slug/reflect"
        element={
          <RequireAuth>
            <main className="app">
              <ReflectPage />
            </main>
          </RequireAuth>
        }
      />

      <Route
        path="/portfolio"
        element={
          <RequireAuth>
            <main className="app">
              <PortfolioPage />
            </main>
          </RequireAuth>
        }
      />

      <Route
        path="/instructor"
        element={
          <RequireAuth>
            <main className="app">
              <InstructorPage />
            </main>
          </RequireAuth>
        }
      />

      <Route
        path="/exercise/:slug"
        element={
          <RequireAuth>
            <main className="app">
              <ExercisePage />
            </main>
          </RequireAuth>
        }
      />

      {/* Anything else goes home rather than showing a blank screen. */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
