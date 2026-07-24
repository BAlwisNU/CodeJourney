import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { api, token } from '../lib/api'

/**
 * Sign up and sign in.
 *
 * One component for both, because they share a layout and half their fields, but
 * they are distinct routes (/signup and /login) so that links, bookmarks and the
 * back button behave the way people expect.
 *
 * Validation runs on submit rather than on every keystroke: telling someone
 * their password is too short while they're still on the third character is
 * noise, not help.
 */

type Mode = 'login' | 'signup'

export function AuthPage({ mode }: { mode: Mode }) {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  // Set by the API client when it clears a dead token.
  const expired = params.get('expired') === '1'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  const isSignup = mode === 'signup'

  function validate(): Record<string, string> {
    const found: Record<string, string> = {}

    if (!email.trim()) found.email = 'We need an email address to sign you in.'
    else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim()))
      found.email = "That doesn't look like an email address."

    if (!password) found.password = 'Please choose a password.'
    else if (isSignup && password.length < 8)
      found.password = 'Passwords need to be at least 8 characters.'
    // bcrypt silently ignores anything past 72 bytes, so a longer passphrase
    // would be weaker than the user believes. Better to say so.
    else if (isSignup && new Blob([password]).size > 72)
      found.password = 'That password is too long — 72 characters at most.'

    if (isSignup) {
      if (!displayName.trim()) found.displayName = 'What should we call you?'
      if (confirm !== password) found.confirm = "These two don't match."
    }

    return found
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const found = validate()
    setErrors(found)
    if (Object.keys(found).length > 0) return

    setBusy(true)
    try {
      // No consent argument: new accounts start opted out, and consent is given
      // (or withdrawn) later on /account. The API still accepts the flag for the
      // mobile client and for tests.
      const response = isSignup
        ? await api.register(email.trim(), password, displayName.trim())
        : await api.login(email.trim(), password)
      token.set(response.access_token)
      navigate('/exercises')
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      // Map the two API errors people actually hit onto the field they need to
      // fix, rather than dropping a generic banner at the top of the form.
      if (message.includes('already registered')) {
        setErrors({
          email: 'There’s already an account with this email. Try logging in.',
        })
      } else if (message.includes('Invalid credentials')) {
        setErrors({ form: "That email and password don't match an account." })
      } else {
        setErrors({ form: message })
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="auth" onSubmit={handleSubmit} noValidate>
      <Link className="muted small" to="/">
        &larr; Back
      </Link>

      <h1>{isSignup ? 'Create your account' : 'Welcome back'}</h1>
      <p className="muted">
        {isSignup
          ? 'You need an account so your work is saved as you go.'
          : 'Log in to pick up where you left off.'}
      </p>

      {expired && (
        <p className="panel panel-hint small">
          You were signed out because your session expired. Log back in and
          you&rsquo;ll pick up exactly where you left off &mdash; nothing you did
          has been lost.
        </p>
      )}

      {errors.form && <p className="panel panel-error small">{errors.form}</p>}

      {isSignup && (
        <Field
          label="What should we call you?"
          error={errors.displayName}
          hint="Shown to you and your instructor. A first name is fine."
        >
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            autoComplete="name"
            autoFocus
          />
        </Field>
      )}

      <Field label="Email" error={errors.email}>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          autoFocus={!isSignup}
        />
      </Field>

      <Field
        label="Password"
        error={errors.password}
        hint={isSignup ? 'At least 8 characters.' : undefined}
      >
        <div className="with-toggle">
          <input
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isSignup ? 'new-password' : 'current-password'}
          />
          <button
            type="button"
            className="toggle"
            onClick={() => setShowPassword((v) => !v)}
            // Typos are invisible in a password field, and a novice mistyping
            // their own password twice at signup is a support problem nobody
            // needs.
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? 'Hide' : 'Show'}
          </button>
        </div>
      </Field>

      {isSignup && (
        <Field label="Password again" error={errors.confirm}>
          <input
            type={showPassword ? 'text' : 'password'}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
          />
        </Field>
      )}

      <button className="primary" disabled={busy}>
        {busy ? 'One sec…' : isSignup ? 'Create account' : 'Log in'}
      </button>

      <p className="muted small centered">
        {isSignup ? (
          <>
            Already have an account? <Link to="/login">Log in</Link>
          </>
        ) : (
          <>
            Haven&rsquo;t got one? <Link to="/signup">Create an account</Link>
          </>
        )}
      </p>
    </form>
  )
}

function Field({
  label,
  error,
  hint,
  children,
}: {
  label: string
  error?: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <label className={error ? 'field field-error' : 'field'}>
      {label}
      {children}
      {hint && !error && <span className="field-hint">{hint}</span>}
      {/* role=alert so screen readers announce the problem rather than leaving
          someone wondering why the form didn't submit. */}
      {error && (
        <span className="field-msg" role="alert">
          {error}
        </span>
      )}
    </label>
  )
}
