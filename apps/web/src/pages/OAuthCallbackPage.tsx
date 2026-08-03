import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { token } from '../lib/api'

/**
 * The landing strip for "Continue with Google / Microsoft".
 *
 * The API finishes the OAuth exchange, then redirects the browser here with our
 * own access token in the URL *fragment* -- `/auth/callback#token=...`. A
 * fragment never leaves the browser: it isn't sent to any server, doesn't reach
 * web-server logs, and isn't passed along in the `Referer` header of whatever
 * the user clicks next. A query string would leak the token to all three.
 *
 * This page exists only to move the token from the URL into storage and get out
 * of the way, so it renders a line of text and nothing else. It replaces its
 * own history entry on the way out, so Back returns to wherever the user
 * started rather than re-running a spent sign-in.
 */

export function OAuthCallbackPage() {
  const navigate = useNavigate()

  // Read during render, not inside the effect, and hold it in state.
  //
  // The effect below scrubs the fragment. Under StrictMode React runs an effect,
  // tears it down and runs it again -- so a second run that re-read the URL
  // would find the fragment it had just erased, conclude there was no token,
  // and bounce a perfectly good sign-in to /login. Capturing the value once
  // makes the effect idempotent: every run sees the same token and reaches the
  // same conclusion, however many times it runs.
  const [fragment] = useState(
    () => new URLSearchParams(window.location.hash.replace(/^#/, ''))
  )
  const granted = fragment.get('token')
  // The API sets this only when the account did not exist a moment ago, so a
  // first-time Google sign-up gets the same welcome step as a first-time
  // password sign-up. Linking a provider to an existing account is not a
  // signup and must not send someone back through it.
  const isNewAccount = fragment.get('new') === '1'

  useEffect(() => {
    if (!granted) {
      // Someone opened this URL directly, or the fragment was stripped. Not an
      // error worth explaining -- send them to the form they wanted.
      navigate('/login', { replace: true })
      return
    }

    token.set(granted)
    // Scrub the token out of the address bar and the history entry before
    // navigating on. Without this it stays visible, and stays in the entry the
    // Back button restores.
    window.history.replaceState(null, '', window.location.pathname)
    navigate(isNewAccount ? '/welcome' : '/exercises', { replace: true })
  }, [granted, isNewAccount, navigate])

  return <p className="muted">Signing you in…</p>
}
