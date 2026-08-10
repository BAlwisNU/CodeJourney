import { useState } from 'react'

import { api } from '../../lib/api'
import type { Classroom } from '../../lib/types'

/**
 * Classes, and the codes that fill them.
 *
 * The code is the biggest thing on the card because of how it gets used: read
 * out to a room, or put on a screen at the front of it. A six-character string
 * in body copy would be squinted at from the back row.
 *
 * There is no invite-by-email flow and that is a decision, not an omission.
 * Asking a teacher to collect thirty addresses before anyone can start is how a
 * class tool goes unused in week one.
 */
export function ClassesView({
  classrooms,
  onChanged,
}: {
  classrooms: Classroom[]
  onChanged: () => void
}) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)

  async function create(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.createClass(name.trim())
      setName('')
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function copy(code: string) {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(code)
      window.setTimeout(() => setCopied(null), 2000)
    } catch {
      // Clipboard access can be refused, and the code is on screen anyway —
      // there is nothing to recover from and nothing worth interrupting for.
    }
  }

  return (
    <div className="tview">
      {classrooms.length > 0 && (
        <div className="tclasses">
          {classrooms.map((classroom) => (
            <article key={classroom.id} className="tclass">
              <h3>{classroom.name}</h3>
              <p className="muted small">
                {classroom.students === 1
                  ? '1 student'
                  : `${classroom.students} students`}
              </p>
              <p className="tcode-label">Class code</p>
              <p className="tcode">{classroom.join_code}</p>
              <button
                type="button"
                className="linkish"
                onClick={() => void copy(classroom.join_code)}
              >
                {copied === classroom.join_code ? 'Copied' : 'Copy code'}
              </button>
            </article>
          ))}
        </div>
      )}

      <section className="tcard tcard-narrow">
        <h2>{classrooms.length ? 'Start another class' : 'Start your first class'}</h2>
        <p className="muted small">
          You&rsquo;ll get a code to read out. Students enter it once and appear
          on your dashboard.
        </p>
        <form className="tnew" onSubmit={create}>
          <label className="field">
            Class name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={120}
              placeholder="Year 9 Computing"
              autoFocus={classrooms.length === 0}
            />
          </label>
          {error && <p className="panel panel-error small">{error}</p>}
          <button className="primary" disabled={busy || !name.trim()}>
            {busy ? 'Creating…' : 'Create class'}
          </button>
        </form>
      </section>

      <p className="trule">
        Students keep their work if they leave a class, and you only ever see
        students who joined one of yours.
      </p>
    </div>
  )
}
