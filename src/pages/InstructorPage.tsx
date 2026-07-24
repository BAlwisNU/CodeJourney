import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { InstructorOverview } from '../lib/types'

/**
 * Instructor analytics: who needs help, and what is the class getting wrong.
 *
 * Students who have exhausted the hint ladder and are still failing sort to the
 * top. That's the whole point — an alphabetical list of names would make the
 * instructor do the triage the platform already has the data to do.
 */
export function InstructorPage() {
  const [data, setData] = useState<InstructorOverview | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .instructor()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  if (error)
    return (
      <p className="panel panel-error">
        {error.includes('Instructor')
          ? 'This page is for instructors.'
          : error}
      </p>
    )
  if (!data) return <p className="muted">Loading…</p>

  const struggling = data.students.filter((s) => s.needs_help)

  return (
    <div className="dash">
      <header className="dash-head">
        <div>
          <h1>Class overview</h1>
          <p className="muted">
            {data.total_students} students · {data.total_submissions} graded
            submissions
          </p>
        </div>
        <Link className="link" to="/exercises">
          My work
        </Link>
      </header>

      {struggling.length > 0 && (
        <section className="panel panel-hint">
          <h2>Could use a hand ({struggling.length})</h2>
          <p className="muted small">
            These students have worked all the way through the hint ladder and
            are still stuck. The platform has nothing left to give them.
          </p>
          <ul className="chips">
            {struggling.map((student) => (
              <span key={student.user_id} className="badge">
                {student.display_name}
              </span>
            ))}
          </ul>
        </section>
      )}

      <section className="panel">
        <h2>Everyone</h2>
        <div className="table-scroll">
          <table className="grid">
            <thead>
              <tr>
                <th>Student</th>
                <th>Solved</th>
                <th>Attempts</th>
                <th>Deepest hint</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.students.map((student) => (
                <tr
                  key={student.user_id}
                  className={student.needs_help ? 'row-flag' : undefined}
                >
                  <td>{student.display_name}</td>
                  <td>
                    {student.solved}/{student.total_exercises}
                  </td>
                  <td>{student.attempts}</td>
                  {/* Instructors DO see hint depth. Measurement reactivity is a
                      concern about showing participants their own dependent
                      variables; the instructor isn't the participant. */}
                  <td>L{student.max_hint_level}</td>
                  <td>
                    {student.needs_help && (
                      <span className="badge badge-flag">needs help</span>
                    )}
                  </td>
                </tr>
              ))}
              {data.students.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">
                    No students enrolled yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2>What the class is getting wrong</h2>
        {data.common_errors.length === 0 ? (
          <p className="muted small">No errors recorded yet.</p>
        ) : (
          <ul className="errbars">
            {data.common_errors.map((error) => {
              const top = data.common_errors[0].count
              return (
                <li key={error.error_type}>
                  <span className="errname">{error.error_type}</span>
                  <span className="muted small">{error.count}</span>
                  <div className="bar bar-sm">
                    <span style={{ width: `${(error.count / top) * 100}%` }} />
                  </div>
                </li>
              )
            })}
          </ul>
        )}
        <p className="muted small">
          Useful for deciding what to reteach, and for telling the content author
          which error translations are earning their keep.
        </p>
      </section>

      {/* Should always be zero. Non-zero means the browser and the server
          disagreed about identical code -- a platform fault, and those rows need
          excluding before analysis. See docs/architecture.md. */}
      {data.divergence_incidents > 0 && (
        <section className="panel panel-error">
          <h2>{data.divergence_incidents} run/submit divergences</h2>
          <p className="small">
            The browser and the server disagreed about the same code. This is a
            platform fault, not a student one. These submissions need inspecting
            before any analysis.
          </p>
        </section>
      )}
    </div>
  )
}
