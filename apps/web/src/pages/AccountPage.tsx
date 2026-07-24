import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api, token } from '../lib/api'
import type { Account } from '../lib/types'

/**
 * Account settings, which in practice means one thing: consent.
 *
 * Withdrawing has to be as easy as granting, and visible without asking anyone.
 * A right to withdraw that requires emailing a researcher is a right on paper
 * only, and it is the first participant protection an ethics committee looks for.
 */
export function AccountPage() {
  const navigate = useNavigate()
  const [account, setAccount] = useState<Account | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [justChanged, setJustChanged] = useState(false)

  useEffect(() => {
    api
      .me()
      .then(setAccount)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  async function toggleConsent(next: boolean) {
    setBusy(true)
    setJustChanged(false)
    try {
      setAccount(await api.setConsent(next))
      setJustChanged(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  if (error) return <p className="panel panel-error">{error}</p>
  if (!account) return <p className="muted">Loading…</p>

  const consenting = account.consented_at !== null

  return (
    <div className="dash">
      <header className="dash-head">
        <div>
          <h1>Your account</h1>
          <p className="muted">{account.email}</p>
        </div>
        <Link className="link" to="/exercises">
          Back to your work
        </Link>
      </header>

      <section className="panel">
        <h2>Name</h2>
        <p className="muted">{account.display_name}</p>
      </section>

      <section className="panel">
        <h2>Helping with the research</h2>

        <p className="muted">
          CodeJourney is a student project studying whether exercises about your
          own life help people learn to code. Taking part means your exercise
          attempts can be used, anonymously, in that research.
        </p>

        <ul className="honest-list">
          <li>
            <strong>Your journal is never included</strong>, and is never read by
            an AI.
          </li>
          <li>
            <strong>The site works exactly the same either way.</strong> Nothing
            is withheld if you opt out.
          </li>
          <li>
            <strong>You can change your mind at any time</strong>, right here.
            Opting out later doesn&rsquo;t delete your work or your progress.
          </li>
        </ul>

        <div className="consent-state">
          <p>
            {consenting ? (
              <>
                <span className="dot dot-on" aria-hidden /> You&rsquo;re currently
                taking part.
              </>
            ) : (
              <>
                <span className="dot" aria-hidden /> You&rsquo;re not taking part.
              </>
            )}
          </p>

          <button
            className={consenting ? '' : 'primary'}
            onClick={() => toggleConsent(!consenting)}
            disabled={busy}
          >
            {busy
              ? 'One sec…'
              : consenting
                ? 'Withdraw from the research'
                : 'Take part in the research'}
          </button>
        </div>

        {justChanged && (
          <p className="muted small">
            {consenting
              ? 'Thank you — your attempts can now be included.'
              : 'Done. Your data will not be used in the research. Everything you have made is still here.'}
          </p>
        )}
      </section>

      <section className="panel">
        <h2>Signing out</h2>
        <p className="muted small">
          Your work is saved on our server, not in this browser, so you can log
          back in anywhere and pick up where you left off.
        </p>
        <button
          onClick={() => {
            token.clear()
            navigate('/')
          }}
        >
          Log out
        </button>
      </section>
    </div>
  )
}
