import { useEffect, useState } from 'react'

import { api, token } from './api'
import type { Account } from './types'

/**
 * Who is signed in, fetched once per token and shared by everyone who asks.
 *
 * This exists because three separate things now need the same answer — the
 * demo banner needs `is_demo`, the router needs `role` to decide whether
 * someone gets the student app or the teaching app, and the account page needs
 * both. Without one cache that would be three /auth/me calls on every page.
 *
 * Keyed on the token, so signing out and back in as somebody else re-asks
 * rather than serving the previous account's answer. Getting that wrong would
 * be worse here than it was for the demo banner: a stale `instructor` would
 * route a student at a dashboard of other people's data, and while the API
 * would refuse every request behind it, the right answer is not to ask.
 */

let cache: { token: string; account: Promise<Account | null> } | null = null

export function loadAccount(): Promise<Account | null> {
  const key = token.get() ?? ''
  // Nobody signed in: no request to make, and /auth/me would 401.
  if (!key) return Promise.resolve(null)
  if (cache?.token === key) return cache.account

  // Silent on failure. Every page handles its own auth errors, and the callers
  // here are choosing a layout, not guarding data — the API is the authority on
  // what anyone may actually read.
  const account = api.me().catch<Account | null>(() => null)
  cache = { token: key, account }
  return account
}

/** Drop the cached account. Called on sign-out, and after anything that
 *  changes the account's own shape. */
export function forgetAccount(): void {
  cache = null
}

type State = { account: Account | null; loading: boolean }

export function useAccount(): State {
  const [state, setState] = useState<State>({ account: null, loading: true })

  useEffect(() => {
    let live = true
    void loadAccount().then((account) => {
      if (live) setState({ account, loading: false })
    })
    return () => {
      live = false
    }
  }, [])

  return state
}

/** True once we know they're a teacher; null while we're still asking.
 *  Three states, not two — rendering a student layout during the wait and
 *  swapping it a moment later is worse than waiting. */
export function useIsTeacher(): boolean | null {
  const { account, loading } = useAccount()
  if (loading) return null
  return account?.role === 'instructor'
}
