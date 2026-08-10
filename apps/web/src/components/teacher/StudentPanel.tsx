import { useEffect, useState } from 'react'

import { Rule, StruggleBar, ago } from './parts'
import { api } from '../../lib/api'
import type { Reflection, TeacherStudentDetail } from '../../lib/types'

/**
 * One student, opened from anywhere their name appears.
 *
 * A panel rather than a page: checking on someone is a glance in the middle of
 * another task, and losing your place in the roster to take it is a poor trade.
 *
 * The journal is behind a deliberate second click. Instructors may read it —
 * the proposal says so and students are told so at signup — but it is private
 * writing about struggling, and putting it on screen automatically next to
 * attempt counts would make it feel like another metric. It is not one. What
 * must never happen either way is a machine reading it: no summarising, no
 * sentiment scoring, no flagging, anywhere in this codebase.
 */
export function StudentPanel({
  userId,
  onClose,
}: {
  userId: string
  onClose: () => void
}) {
  const [detail, setDetail] = useState<TeacherStudentDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [journal, setJournal] = useState<Reflection[] | null>(null)
  const [openJournal, setOpenJournal] = useState(false)

  useEffect(() => {
    let live = true
    setDetail(null)
    api
      .teacherStudent(userId)
      .then((d) => live && setDetail(d))
      .catch((e) => live && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      live = false
    }
  }, [userId])

  useEffect(() => {
    if (!openJournal || journal) return
    let live = true
    api
      .teacherStudentReflections(userId)
      .then((r) => live && setJournal(r))
      .catch(() => live && setJournal([]))
    return () => {
      live = false
    }
  }, [openJournal, journal, userId])

  // Escape closes, because a panel that traps you is worse than no panel.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <>
      <div className="tscrim" onClick={onClose} aria-hidden />
      <aside className="tpanel" role="dialog" aria-label="Student detail">
        <header className="tpanel-head">
          <h2>{detail?.display_name ?? 'Student'}</h2>
          <button type="button" className="tclose" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>

        {error && <p className="panel panel-error">{error}</p>}
        {!detail && !error && <p className="muted">Loading…</p>}

        {detail && (
          <>
            <div className="tpanel-stats">
              <div>
                <dt>Solved</dt>
                <dd>
                  {detail.solved}
                  <span className="muted">/{detail.total_exercises}</span>
                </dd>
              </div>
              <div>
                <dt>Attempts</dt>
                <dd>{detail.attempts}</dd>
              </div>
              <div>
                <dt>Deepest hint</dt>
                <dd>
                  {detail.max_hint_level === 0 ? '—' : `L${detail.max_hint_level}`}
                </dd>
              </div>
              <div>
                <dt>Last seen</dt>
                <dd className="tpanel-when">{ago(detail.last_active_at)}</dd>
              </div>
            </div>

            {detail.stuck_on && (
              <p className="tpanel-stuck">
                Out of hints on <b>{detail.stuck_on}</b> and still going.
              </p>
            )}

            <section>
              <h3>Where they struggled</h3>
              {detail.hardest.length === 0 ? (
                <p className="muted small">No graded attempts yet.</p>
              ) : (
                <ul className="tdiff">
                  {detail.hardest.map((stat) => (
                    <li key={stat.key}>
                      <span className="tdiff-label">{stat.label}</span>
                      <StruggleBar stat={stat} />
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h3>Their journal</h3>
              <Rule>
                Private writing about how the work felt. Yours to read, never
                read by any machine &mdash; it is never scored, summarised or
                flagged.
              </Rule>
              {!openJournal ? (
                <button
                  type="button"
                  className="linkish"
                  onClick={() => setOpenJournal(true)}
                >
                  Read it
                </button>
              ) : journal === null ? (
                <p className="muted small">Loading…</p>
              ) : journal.length === 0 ? (
                <p className="muted small">They haven&rsquo;t written any yet.</p>
              ) : (
                <ul className="tjournal">
                  {journal.map((entry) => (
                    <li key={entry.id}>
                      <p>
                        <b>Tried</b> {entry.what_i_tried}
                      </p>
                      <p>
                        <b>Stuck</b> {entry.where_i_got_stuck}
                      </p>
                      <p>
                        <b>Fixed</b> {entry.how_i_fixed_it}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </aside>
    </>
  )
}
