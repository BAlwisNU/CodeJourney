import { useEffect, useState } from 'react'

import { api } from '../lib/api'
import type { MyClass } from '../lib/types'

/**
 * Join a class with the code the teacher read out.
 *
 * Lives on the account page: joining is a once-a-term act, and putting it in
 * the daily flow would give it a prominence it does not earn.
 *
 * What joining actually does is worth being straight about on screen, because
 * it changes who can see what — so the copy says it plainly rather than burying
 * it in a policy page nobody opens.
 */
export function JoinClass() {
  const [classes, setClasses] = useState<MyClass[] | null>(null)
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    api
      .myClasses()
      .then((c) => live && setClasses(c))
      .catch(() => live && setClasses([]))
    return () => {
      live = false
    }
  }, [])

  if (classes === null) return null

  async function join(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const joined = await api.joinClass(code.trim())
      setClasses((current) => [...(current ?? []), joined])
      setCode('')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function leave(id: string) {
    await api.leaveClass(id)
    setClasses((current) => (current ?? []).filter((c) => c.id !== id))
  }

  return (
    <section className="panel">
      <h2>Your class</h2>

      {classes.length > 0 ? (
        <ul className="joined">
          {classes.map((c) => (
            <li key={c.id}>
              <span>
                <b>{c.name}</b>
                <span className="muted small"> · {c.teacher_name}</span>
              </span>
              <button
                type="button"
                className="linkish"
                onClick={() => void leave(c.id)}
              >
                Leave
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted small">
          You&rsquo;re not in a class. If you&rsquo;re learning on your own, you
          don&rsquo;t need one &mdash; everything works either way.
        </p>
      )}

      <form className="join-form" onSubmit={join}>
        <label className="field">
          Class code
          <input
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            maxLength={16}
            placeholder="ABC123"
            className="join-code"
            autoComplete="off"
            spellCheck={false}
          />
          <span className="field-hint">
            Six characters, from your teacher.
          </span>
        </label>
        {error && <p className="panel panel-error small">{error}</p>}
        <button className="primary" disabled={busy || !code.trim()}>
          {busy ? 'Joining…' : 'Join'}
        </button>
      </form>

      {/* Said here rather than in a policy page, because this is the moment it
          becomes true. */}
      <p className="muted small">
        Joining lets your teacher see how you&rsquo;re getting on, and lets you
        ask them questions from inside a lesson. Leaving keeps everything
        you&rsquo;ve made.
      </p>
    </section>
  )
}
