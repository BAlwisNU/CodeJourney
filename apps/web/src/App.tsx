import { Navigate, Route, Routes } from 'react-router-dom'

import { token } from './lib/api'
import { DashboardPage } from './pages/DashboardPage'
import { ExercisePage } from './pages/ExercisePage'
import { LandingPage } from './pages/LandingPage'
import { AccountPage } from './pages/AccountPage'
import { AuthPage } from './pages/AuthPage'
import { InstructorPage } from './pages/InstructorPage'
import { PlanPage } from './pages/PlanPage'
import { PortfolioPage } from './pages/PortfolioPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  // Presence check only. The API is the authority on whether a token is valid;
  // this just avoids rendering a page that's about to 401.
  if (!token.get()) return <Navigate to="/login" replace />
  return <>{children}</>
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
            <main className="app">
              <DashboardPage />
            </main>
          </RequireAuth>
        }
      />

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
