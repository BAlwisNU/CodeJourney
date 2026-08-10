import type { Difficulty } from '../../lib/types'

/**
 * Small pieces shared across the teaching views.
 *
 * Here rather than duplicated per view because two of them encode a *rule*, not
 * a style: what "struggled" counts, and how long ago is long enough to matter.
 * A rule copied into four files becomes four rules the first time one of them
 * is edited.
 */

/** How long ago, in the words a person would use out loud. */
export function ago(iso: string | null): string {
  if (!iso) return 'not yet'
  const minutes = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutes < 2) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days === 1) return 'yesterday'
  if (days < 14) return `${days} days ago`
  return `${Math.floor(days / 7)} weeks ago`
}

/**
 * A bar showing what share of the class struggled with something.
 *
 * The count leads and the rate follows, in that order deliberately: "9 of 22"
 * is a number a teacher can act on, and a bare 41% hides whether that is nine
 * students or one.
 */
export function StruggleBar({ stat }: { stat: Difficulty }) {
  const pct = Math.round(stat.struggle_rate * 100)
  return (
    <div className="tstruggle">
      <div className="tstruggle-bar" aria-hidden>
        <span style={{ width: `${pct}%` }} />
      </div>
      <span className="tstruggle-num">
        {stat.struggled} of {stat.attempted}
        <span className="muted"> · {pct}%</span>
      </span>
    </div>
  )
}

/** Why a number says what it says. Shown next to the measure, not in a footnote:
 *  a teacher asked to trust "difficult" deserves to know what was measured. */
export function Rule({ children }: { children: React.ReactNode }) {
  return <p className="trule">{children}</p>
}

export function Empty({
  title,
  children,
}: {
  title: string
  children?: React.ReactNode
}) {
  return (
    <div className="tempty">
      <h3>{title}</h3>
      {children}
    </div>
  )
}
