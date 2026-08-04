import { useEffect, useState } from 'react'

import { DEMO_KIND_KEY, api, token } from './api'

/**
 * Whether the signed-in account is a demo, and which button minted it.
 *
 * Shared by the banner and the flow nav, so the answer is fetched once per
 * session rather than once per component. Without the cache, every page load
 * would ask /auth/me twice for the same fact.
 *
 * The cache is keyed on the token, so logging out and back in as somebody else
 * re-asks rather than serving the previous account's answer -- a stale `true`
 * here would put a "this is a demo" banner over a real user's work.
 */

export type DemoKind = 'lesson' | 'account' | null

/**
 * The demo kind as recorded locally at the moment the button was pressed.
 *
 * Readable synchronously, which the landing page needs: it has to decide
 * whether someone is "signed in" during the first render, and an answer that
 * arrives a moment later would show the wrong navigation and then swap it.
 *
 * The server remains the authority -- this is a hint, not a claim.
 */
export const demoMarker = {
  get: (): DemoKind => localStorage.getItem(DEMO_KIND_KEY) as DemoKind,
  set: (kind: Exclude<DemoKind, null>) => localStorage.setItem(DEMO_KIND_KEY, kind),
}

/**
 * Leave a demo: throw away the throwaway account.
 *
 * A lesson demo is a look at one exercise, not a session. Someone who tries it
 * and goes back to the home page should see the site as a visitor does -- with
 * "Start free" and the demo buttons -- rather than "Keep going", which implies
 * an account they never made and cannot get back into.
 */
export function endDemo(): void {
  token.clear()
  cache = null
}

let cache: { token: string; answer: Promise<DemoKind> } | null = null

function load(): Promise<DemoKind> {
  const key = token.get() ?? ''
  // Nobody is signed in: no request to make, and /auth/me would 401.
  if (!key) return Promise.resolve(null)
  if (cache?.token === key) return cache.answer

  const answer = api
    .me()
    .then((account) => (account.is_demo ? (account.demo_kind as DemoKind) : null))
    // Silent: every page already handles its own auth failures, and this only
    // decides whether to show a banner and hide one link.
    .catch<DemoKind>(() => null)

  cache = { token: key, answer }
  return answer
}

export function useDemoKind(): DemoKind {
  const [kind, setKind] = useState<DemoKind>(null)

  useEffect(() => {
    let live = true
    void load().then((value) => {
      if (live) setKind(value)
    })
    return () => {
      live = false
    }
  }, [])

  return kind
}
