import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { AskState } from '../lib/types'

/**
 * Ask a person.
 *
 * The platform has three other ways to get unstuck and all three decide for
 * themselves what you need: the hint ladder escalates on failure counts, the
 * flag fires when you exhaust it, and the AI tutor answers what it was asked
 * about the code in front of it. This is the one place a student sets the
 * agenda — including for the questions none of those can take, like "I've
 * missed two weeks and I don't know where to start".
 *
 * Sits next to the tutor on the Reflect page rather than replacing it. They are
 * different offers and the student should be able to tell which is which, so
 * this one says plainly that a human will read it and that it will not be
 * instant.
 */
export function AskTeacher({
  exerciseSlug,
  showHeading = true,
}: {
  exerciseSlug?: string
  /** False where the surrounding tab is already labelled "Ask your teacher" --
   *  the same words twice, a line apart, read as a mistake. */
  showHeading?: boolean
}) {
  const [state, setState] = useState<AskState | null>(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)

  useEffect(() => {
    let live = true
    api
      .myQuestions()
      .then((s) => live && setState(s))
      .catch(() => live && setState(null))
    return () => {
      live = false
    }
  }, [])

  if (!state) return null

  // No class, no teacher listening. Say how to fix it rather than showing a box
  // that takes a message nobody will read.
  if (!state.can_ask) {
    return (
      <section className="panel ask">
        {showHeading && <h2>Ask your teacher</h2>}
        <p className="muted small">
          You&rsquo;re not in a class yet. If you have a class code, add it on
          your <Link to="/account">account page</Link> and you can ask your
          teacher from here.
        </p>
      </section>
    )
  }

  const mine = state.requests.filter((r) => r.status !== 'closed')

  async function send(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const created = await api.askTeacher(draft.trim(), exerciseSlug)
      setState((current) =>
        current ? { ...current, requests: [created, ...current.requests] } : current
      )
      setDraft('')
      setSent(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function close(id: string) {
    const updated = await api.closeQuestion(id)
    setState((current) =>
      current
        ? {
            ...current,
            requests: current.requests.map((r) => (r.id === id ? updated : r)),
          }
        : current
    )
  }

  return (
    <section className="panel ask">
      {showHeading && <h2>Ask your teacher</h2>}
      <p className="muted small">
        {state.teachers.length === 1
          ? `${state.teachers[0]} will see this.`
          : `${state.teachers.join(' and ')} will see this.`}{' '}
        A real person, so not straight away &mdash; you&rsquo;ll find the answer
        back here.
      </p>

      {mine.length > 0 && (
        <ul className="ask-list">
          {mine.map((request) => (
            <li key={request.id} className={`ask-item is-${request.status}`}>
              <p className="ask-q">{request.body}</p>
              {request.status === 'answered' ? (
                <>
                  <p className="ask-a">
                    <span className="ask-a-who">{request.answered_by}</span>
                    {request.answer}
                  </p>
                  <button
                    type="button"
                    className="linkish"
                    onClick={() => void close(request.id)}
                  >
                    That helped &mdash; close it
                  </button>
                </>
              ) : (
                <p className="muted small">Waiting for an answer.</p>
              )}
            </li>
          ))}
        </ul>
      )}

      <form className="ask-form" onSubmit={send}>
        <label className="field">
          <span className="sr-only">Your question</span>
          <textarea
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value)
              setSent(false)
            }}
            rows={3}
            maxLength={4000}
            placeholder="What&rsquo;s confusing you? Say as much as you like."
          />
        </label>
        {error && <p className="panel panel-error small">{error}</p>}
        {sent && !error && (
          <p className="ask-sent small">Sent. Your teacher will see it.</p>
        )}
        <button className="primary" disabled={busy || !draft.trim()}>
          {busy ? 'Sending…' : 'Send it'}
        </button>
      </form>
    </section>
  )
}
