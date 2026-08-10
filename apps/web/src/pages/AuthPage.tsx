import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { ProviderMark } from '../components/ProviderMark'
import { API_BASE, api, token } from '../lib/api'
import { forgetAccount, loadAccount } from '../lib/session'

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
  // Set by the OAuth callback when a third-party sign-in didn't complete. The
  // API writes these messages for the user, so they are shown verbatim.
  const oauthError = params.get('error')

  // Which "Continue with…" buttons this deployment can actually offer. Empty
  // until the API answers, and stays empty if it can't -- the email form below
  // works either way, so a failed lookup must not block signing in.
  const [providers, setProviders] = useState<
    { key: string; label: string; configured: boolean }[]
  >([])
  useEffect(() => {
    let live = true
    api
      .oauthProviders()
      .then((result) => {
        if (live) setProviders(result.providers)
      })
      .catch(() => {
        /* No buttons. Deliberately silent: nothing here is broken for the user. */
      })
    return () => {
      live = false
    }
  }, [])

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  // Which kind of account. Learners are the overwhelming majority, so that is
  // the default and the teacher option is one click away rather than a decision
  // everyone has to make before they can start typing.
  const [asTeacher, setAsTeacher] = useState(false)
  const [teacherCode, setTeacherCode] = useState('')

  // Whether this deployment offers teacher accounts at all. Until the API says
  // yes, the choice isn't drawn -- a server with it switched off shouldn't
  // advertise a door that is locked.
  const [teachersWelcome, setTeachersWelcome] = useState(false)
  useEffect(() => {
    let live = true
    api
      .teacherSignupAvailable()
      .then((r) => live && setTeachersWelcome(r.enabled))
      .catch(() => {
        /* Not offered. The learner form below is unaffected. */
      })
    return () => {
      live = false
    }
  }, [])

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  const isSignup = mode === 'signup'
  // "Sign in with Google" / "Sign up with Google" -- the wording both providers'
  // brand guidelines list, and what people are used to reading on these.
  const verb = isSignup ? 'Sign up' : 'Sign in'

  // Which provider's setup note to show, once someone presses a button that has
  // no credentials behind it. Development only; see the buttons below.
  const [setupHint, setSetupHint] = useState<string | null>(null)

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
      if (asTeacher && !teacherCode.trim())
        found.teacherCode = 'Teacher accounts need the code for your school.'
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
      let response
      if (isSignup && asTeacher) {
        response = await api.registerTeacher(
          email.trim(),
          password,
          displayName.trim(),
          teacherCode.trim()
        )
      } else if (isSignup) {
        response = await api.register(email.trim(), password, displayName.trim())
      } else {
        response = await api.login(email.trim(), password)
      }
      token.set(response.access_token)
      // The account is new, so nothing cached about the previous one applies.
      forgetAccount()

      if (isSignup && asTeacher) {
        // Teachers skip /welcome entirely: it asks what you want to learn and
        // what you'd like to build, which is not the question being put to
        // someone who came here to run a class.
        navigate('/teach')
      } else if (isSignup) {
        // Straight to the conversation. Step two used to be a form -- goals,
        // experience, how you learn, how much time, what worries you -- and a
        // beginner's first sight of the product was six fields about
        // themselves. The coach asks the same things now, one at a time, and
        // answers back.
        navigate('/welcome/chat')
      } else {
        // Logging in: the API knows which app this person belongs in, and
        // asking it beats guessing. A failed lookup falls through to the
        // student app, which is where all but a handful of accounts live.
        const account = await loadAccount()
        navigate(account?.role === 'instructor' ? '/teach' : '/exercises')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      // Map the API errors people actually hit onto the field they need to
      // fix, rather than dropping a generic banner at the top of the form.
      if (message.includes('already registered')) {
        setErrors({
          email: 'There’s already an account with this email. Try logging in.',
        })
      } else if (message.includes('Invalid credentials')) {
        setErrors({ form: "That email and password don't match an account." })
      } else if (message.includes('teacher code')) {
        setErrors({ teacherCode: message })
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
          ? asTeacher
            ? 'A teacher account gives you a class code and a dashboard of how your students are getting on.'
            : 'You need an account so your work is saved as you go.'
          : 'Log in to pick up where you left off.'}
      </p>

      {/* Only on signup, and only where the deployment offers it. Logging in
          needs no choice: the account already knows which it is. */}
      {isSignup && teachersWelcome && (
        <div className="role-pick" role="radiogroup" aria-label="What are you here for?">
          <button
            type="button"
            role="radio"
            aria-checked={!asTeacher}
            className={asTeacher ? 'role-opt' : 'role-opt is-on'}
            onClick={() => setAsTeacher(false)}
          >
            <span className="role-opt-title">I&rsquo;m learning</span>
            <span className="role-opt-note">Lessons, projects, and a coach.</span>
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={asTeacher}
            className={asTeacher ? 'role-opt is-on' : 'role-opt'}
            onClick={() => setAsTeacher(true)}
          >
            <span className="role-opt-title">I&rsquo;m teaching</span>
            <span className="role-opt-note">
              A class to run and students to keep an eye on.
            </span>
          </button>
        </div>
      )}

      {expired && (
        <p className="panel panel-hint small">
          You were signed out because your session expired. Log back in and
          you&rsquo;ll pick up exactly where you left off &mdash; nothing you did
          has been lost.
        </p>
      )}

      {(errors.form || oauthError) && (
        <p className="panel panel-error small">{errors.form ?? oauthError}</p>
      )}

      {/* Hidden for teacher signup, because those buttons do not do what they
          appear to: /auth/oauth/…/start mints a STUDENT account, and there is no
          way to carry the teacher code through the provider round trip. A
          teacher pressing Google would end up with the wrong kind of account and
          nothing on screen explaining why. */}
      {isSignup && asTeacher && providers.length > 0 && (
        <p className="oauth-setup-note small">
          Teacher accounts are made with an email address and your school&rsquo;s
          code. Google, Microsoft and the rest sign you up as a student.
        </p>
      )}

      {providers.length > 0 && !(isSignup && asTeacher) && (
        <>
          {/* The verb lives here rather than on each tile. Six buttons reading
              "Sign in with X" is six repetitions of the same three words, and at
              this width the names would have to be truncated to fit them. */}
          <p className="oauth-caption">{verb} with</p>

          <div className="oauth-buttons">
            {providers.map((provider) =>
              provider.configured ? (
                <a
                  key={provider.key}
                  className="oauth-btn"
                  // A real navigation, not fetch: the browser has to follow the
                  // redirect out to the provider and back, which XHR cannot do.
                  // An anchor also gets middle-click and keyboard activation for
                  // free, where a button would need both wired by hand.
                  href={`${API_BASE}/auth/oauth/${provider.key}/start?mode=${mode}`}
                  // The visible text is only the provider's name now, so the
                  // accessible name has to carry the rest -- "Google" on its own
                  // tells a screen-reader user nothing about what it does.
                  aria-label={`${verb} with ${provider.label}`}
                  title={provider.label}
                >
                  <ProviderMark name={provider.key} />
                  <span>{provider.label}</span>
                </a>
              ) : (
                // Development only -- the API never reports an unconfigured
                // provider in production. Drawn identically to a live button so
                // the page looks finished, and says what's missing when pressed
                // rather than sitting there greyed out.
                <button
                  key={provider.key}
                  type="button"
                  className="oauth-btn"
                  onClick={() => setSetupHint(provider.key)}
                  aria-label={`${verb} with ${provider.label}`}
                  title={provider.label}
                >
                  <ProviderMark name={provider.key} />
                  <span>{provider.label}</span>
                </button>
              )
            )}
          </div>

          {setupHint && (
            <p className="oauth-setup-note small">
              {setupHint === 'google' ? 'Google' : 'Microsoft'} sign-in
              isn&rsquo;t set up on this machine yet. Add{' '}
              <code>{setupHint.toUpperCase()}_CLIENT_ID</code> and{' '}
              <code>{setupHint.toUpperCase()}_CLIENT_SECRET</code> to{' '}
              <code>apps/api/.env</code> and restart the API — the README has
              the steps. Only shown in development.
            </p>
          )}
          <p className="or-rule">
            <span>or {isSignup ? 'sign up' : 'log in'} with an email</span>
          </p>
        </>
      )}

      {isSignup && (
        <Field
          label="What should we call you?"
          error={errors.displayName}
          hint={
            asTeacher
              ? 'What your students will see. “Ms Okafor” rather than a first name.'
              : 'Shown to you and your teacher. A first name is fine.'
          }
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

      {/* A teacher account can see its students' progress and read their
          journals, so it cannot be a checkbox anyone can tick. The code comes
          from whoever set CodeJourney up for the school. */}
      {isSignup && asTeacher && (
        <Field
          label="Teacher code"
          error={errors.teacherCode}
          hint="From whoever set up CodeJourney for your school."
        >
          <input
            value={teacherCode}
            onChange={(e) => setTeacherCode(e.target.value)}
            autoComplete="off"
            spellCheck={false}
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
