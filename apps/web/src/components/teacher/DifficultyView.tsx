import { Empty, Rule, StruggleBar } from './parts'
import type { Difficulty, TeacherHome } from '../../lib/types'

/**
 * What the class finds hard — the view a teacher plans from.
 *
 * Two levels, because they answer different questions. A single exercise being
 * hard might be that exercise: an awkward example, a confusing prompt. A whole
 * concept being hard is something to reteach on Monday. Showing only the
 * per-exercise list would bury that distinction under thirty rows.
 *
 * Ranked by the *number* of students who struggled rather than the rate. A rate
 * puts an exercise one student bounced off once above one that half the class
 * is stuck on. Both numbers are shown, because a count without a denominator is
 * its own kind of lie.
 */
export function DifficultyView({ data }: { data: TeacherHome }) {
  if (data.hardest.length === 0) {
    return (
      <Empty title="Nothing to measure yet">
        <p className="muted">
          This fills in as your class submits work. Every graded attempt feeds
          it — nobody has to do anything extra.
        </p>
      </Empty>
    )
  }

  return (
    <div className="tview">
      <Rule>
        A student counts as having <b>struggled</b> with something if they
        attempted it and either never solved it, or needed a level-3 hint or
        deeper to get there. Only graded submits count &mdash; pressing Run in
        their own browser isn&rsquo;t attempting it.
      </Rule>

      <section className="tcard">
        <header className="tcard-head">
          <h2>By topic</h2>
          <span className="muted small">What to reteach</span>
        </header>
        <ul className="tdiff tdiff-lg">
          {data.concepts.map((stat) => (
            <li key={stat.key}>
              <span className="tdiff-label">{stat.label}</span>
              <StruggleBar stat={stat} />
              <Detail stat={stat} />
            </li>
          ))}
        </ul>
      </section>

      <section className="tcard">
        <header className="tcard-head">
          <h2>By lesson</h2>
          <span className="muted small">Hardest first</span>
        </header>
        <ul className="tdiff tdiff-lg">
          {data.hardest.map((stat) => (
            <li key={stat.key}>
              <span className="tdiff-label">{stat.label}</span>
              <StruggleBar stat={stat} />
              <Detail stat={stat} />
            </li>
          ))}
        </ul>
      </section>

      <section className="tcard">
        <header className="tcard-head">
          <h2>What&rsquo;s going wrong</h2>
          <span className="muted small">By Python error</span>
        </header>
        {data.common_errors.length === 0 ? (
          <p className="muted small">No errors recorded yet.</p>
        ) : (
          <ul className="terrors">
            {data.common_errors.map((error) => {
              const top = data.common_errors[0].count
              return (
                <li key={error.error_type}>
                  <code>{error.error_type}</code>
                  <span className="tstruggle-bar" aria-hidden>
                    <span style={{ width: `${(error.count / top) * 100}%` }} />
                  </span>
                  <span className="tnum muted">{error.count}</span>
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </div>
  )
}

function Detail({ stat }: { stat: Difficulty }) {
  return (
    <span className="tdiff-detail muted small">
      {stat.solved} solved it
      {stat.avg_attempts_to_solve !== null && (
        <> &middot; {stat.avg_attempts_to_solve.toFixed(1)} tries on average</>
      )}
      {stat.avg_hint_level > 0 && (
        <> &middot; hints to L{stat.avg_hint_level.toFixed(1)}</>
      )}
      {stat.top_error && (
        <>
          {' '}
          &middot; usually <code>{stat.top_error}</code>
        </>
      )}
    </span>
  )
}
