const LABELS: Record<number, string> = {
  2: 'Where to look',
  3: 'The idea behind it',
  4: 'The shape of it',
}

/**
 * L2-L4 of the ladder. L0 is the test output, L1 is the translated error, L5 is
 * a human being, and the answer is never.
 *
 * The level is shown, not hidden. A student should know the system escalated and
 * roughly how far it can go -- that it stops short of the answer is a promise,
 * and promises only work if they're visible.
 */
export function HintPanel({
  level,
  hint,
  flagged,
}: {
  level: number
  hint: string | null
  flagged?: boolean
}) {
  if (!hint && !flagged) return null

  return (
    <aside className="panel panel-hint">
      {hint && (
        <>
          <h3>
            {LABELS[level] ?? 'A nudge'}
            <span className="badge badge-quiet">hint {level} of 4</span>
          </h3>
          {/* Authored content, and pseudocode skeletons at L4 use newlines
              meaningfully, so preserve them. */}
          <p style={{ whiteSpace: 'pre-wrap' }}>{hint}</p>
        </>
      )}

      {flagged && (
        <p className="muted">
          You&rsquo;ve been at this one a while — we&rsquo;ve let your instructor
          know you might want a hand. Keep going in the meantime; there&rsquo;s no
          limit on tries.
        </p>
      )}
    </aside>
  )
}
