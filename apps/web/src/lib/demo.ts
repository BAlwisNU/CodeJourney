import { useEffect, useState } from 'react'

import { api, token } from './api'

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

let cache: { token: string; answer: Promise<DemoKind> } | null = null

function load(): Promise<DemoKind> {
  const key = token.get() ?? ''
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
