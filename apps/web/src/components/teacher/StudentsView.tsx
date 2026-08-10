import { useState } from 'react'

import { Empty, ago } from './parts'
import type { TeacherHome, TeacherStudent } from '../../lib/types'

/**
 * The roster: everyone, and how they are doing.
 *
 * Arrives sorted by need — anyone flagged or waiting on an answer first, then
 * by how little they have solved. A teacher can re-sort by name when they are
 * looking someone up, which is a different task from triage and deserves its
 * own control rather than being the default.
 *
 * Hint depth is shown here and nowhere in the student's own app. That
 * asymmetry is deliberate and documented: showing participants their own hint
 * depth changes how they use hints, which is the thing being measured. The
 * teacher is not the participant.
 */

type Sort = 'need' | 'name' | 'progress'

export function StudentsView({
  data,
  onOpenStudent,
}: {
  data: TeacherHome
  onOpenStudent: (userId: string) => void
}) {
  const [sort, setSort] = useState<Sort>('need')
  const [query, setQuery] = useState('')

  const filtered = data.students.filter((s) =>
    s.display_name.toLowerCase().includes(query.trim().toLowerCase())
  )
  const rows = [...filtered].sort((a, b) => {
    if (sort === 'name') return a.display_name.localeCompare(b.display_name)
    if (sort === 'progress') return b.solved - a.solved
    return 0 // The server already ordered by need.
  })

  if (data.total_students === 0) {
    return (
      <Empty title="No students yet">
        <p className="muted">
          Give your class the six-character code from the Classes tab. They
          enter it on their account page and appear here straight away.
        </p>
      </Empty>
    )
  }

  return (
    <div className="tview">
      <div className="ttools">
        <input
          className="tsearch"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Find a student"
          aria-label="Find a student"
        />
        <div className="tsegs" role="group" aria-label="Sort by">
          {(
            [
              ['need', 'Needs you'],
              ['progress', 'Furthest on'],
              ['name', 'A–Z'],
            ] as [Sort, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={sort === key ? 'tseg is-on' : 'tseg'}
              aria-pressed={sort === key}
              onClick={() => setSort(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="ttable-wrap">
        <table className="ttable">
          <thead>
            <tr>
              <th>Student</th>
              <th>Progress</th>
              <th>Attempts</th>
              <th>Deepest hint</th>
              <th>Last seen</th>
              <th>Needs</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((student) => (
              <Row key={student.user_id} student={student} onOpen={onOpenStudent} />
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  Nobody by that name.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Row({
  student,
  onOpen,
}: {
  student: TeacherStudent
  onOpen: (userId: string) => void
}) {
  const pct = student.total_exercises
    ? Math.round((student.solved / student.total_exercises) * 100)
    : 0

  return (
    <tr className={student.needs_help ? 'is-flagged' : undefined}>
      <td>
        <button type="button" className="tlink" onClick={() => onOpen(student.user_id)}>
          {student.display_name}
        </button>
        {student.stuck_on && (
          <span className="tstuck">stuck on {student.stuck_on}</span>
        )}
      </td>
      <td>
        <div className="tprog">
          <span className="tprog-bar" aria-hidden>
            <span style={{ width: `${pct}%` }} />
          </span>
          <span className="tprog-num">
            {student.solved}/{student.total_exercises}
          </span>
        </div>
      </td>
      <td className="tnum">{student.attempts}</td>
      <td className="tnum">
        {student.max_hint_level === 0 ? '—' : `L${student.max_hint_level}`}
      </td>
      <td className="muted small">{ago(student.last_active_at)}</td>
      <td>
        <span className="tflags">
          {student.open_questions > 0 && (
            <span className="tbadge is-ask">
              {student.open_questions === 1
                ? 'asked you'
                : `${student.open_questions} questions`}
            </span>
          )}
          {student.needs_help && <span className="tbadge is-flag">out of hints</span>}
          {!student.needs_help && !student.open_questions && student.attempts === 0 && (
            <span className="tbadge is-quiet">not started</span>
          )}
        </span>
      </td>
    </tr>
  )
}
