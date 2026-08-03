import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'

/**
 * Says out loud that this is a demo.
 *
 * Shown on every signed-in page when the account came from one of the landing
 * page's demo buttons. Without it a demo is indistinguishable from a real
 * account: someone spends twenty minutes writing code, comes back a week later,
 * and it is gone -- with nothing on screen having warned them. On a site whose
 * whole pitch is that it explains itself honestly, that would be a poor first
 * impression to design in.
 *
 * `is_demo` comes from the server, derived from the account's address rather
 * than stored, so it cannot fall out of step with what the account really is.
 * Renders nothing at all for a normal account, and nothing while it is still
 * asking -- a banner that flashes on and off during page load would be worse
 * than one that arrives a moment late.
 */
export function DemoBanner() {
  const [isDemo, setIsDemo] = useState(false)

  useEffect(() => {
    let live = true
    api
      .me()
      .then((account) => {
        if (live) setIsDemo(account.is_demo)
      })
      .catch(() => {
        // Silent: every page here already handles its own auth failures, and a
        // second error message about the banner helps nobody.
      })
    return () => {
      live = false
    }
  }, [])

  if (!isDemo) return null

  return (
    <p className="demo-banner" role="status">
      <span className="demo-badge">Demo</span>
      You&rsquo;re exploring a demo account — have a look around, but nothing
      here is saved for long.{' '}
      <Link to="/signup">Create a free account</Link> to keep what you make.
    </p>
  )
}
