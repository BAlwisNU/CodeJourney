import { Link } from 'react-router-dom'

import { useDemoKind } from '../lib/demo'

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
 * The flag comes from the server, derived from the account's address rather
 * than stored, so it cannot fall out of step with what the account really is.
 * Renders nothing at all for a normal account, and nothing while it is still
 * asking -- a banner that flashes on and off during page load would be worse
 * than one that arrives a moment late.
 */
export function DemoBanner() {
  // Shared with FlowNav and cached per token, so the two of them ask /auth/me
  // once between them rather than once each.
  const kind = useDemoKind()

  if (kind === null) return null

  return (
    <p className="demo-banner" role="status">
      <span className="demo-badge">Demo</span>
      {/* The two buttons are different offers and should not describe
          themselves identically. Somebody who pressed "Demo Lesson" was not
          handed an account to explore -- telling them they were invites the
          question of where it is. */}
      {kind === 'lesson' ? (
        <>
          You&rsquo;re trying a sample lesson. Nothing here is saved.{' '}
          <Link to="/signup">Create a free account</Link> to keep your work.
        </>
      ) : (
        <>
          You&rsquo;re exploring a demo account — have a look around, but
          nothing here is saved for long.{' '}
          <Link to="/signup">Create a free account</Link> to keep what you make.
        </>
      )}
    </p>
  )
}
