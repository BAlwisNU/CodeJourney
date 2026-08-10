import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Empty, ago } from './parts'
import { api } from '../../lib/api'
import type { HelpRequest } from '../../lib/types'

/**
 * The questions students asked, and the box to answer them in.
 *
 * The only place in the platform where a student set the agenda. The hint
 * ladder escalates on failure counts, the flag fires when someone exhausts it,
 * and the AI tutor talks when spoken to — all three decide for themselves what
 * is worth surfacing. Here, a person decided.
 *
 * Oldest first, on purpose. A queue sorted newest-first quietly buries whoever
 * has been waiting longest, which is the opposite of what a queue is for.
 */
export function QuestionsView({ classroomId }: { classroomId?: string }) {
  const [rows, setRows] = useState<HelpRequest[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showAnswered, setShowAnswered] = useState(false)

  useEffect(() => {
    let live = true
    api
      .helpInbox(classroomId)
      .then((r) => live && setRows(r))
      .catch((e) => live && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      live = false
    }
  }, [classroomId])

  if (error) return <p className="panel panel-error">{error}</p>
  if (!rows) return <p className="muted">Loading…</p>

  const open = rows.filter((r) => r.status === 'open')
  const answered = rows.filter((r) => r.status === 'answered')

  function replace(next: HelpRequest) {
    setRows((current) => (current ?? []).map((r) => (r.id === next.id ? next : r)))
    // Answering moves the card out of "waiting on you" and into the answered
    // list, which is collapsed. Left alone it would simply vanish, with nothing
    // on screen confirming the reply was sent -- so open the section it went to.
    setShowAnswered(true)
  }

  if (rows.length === 0) {
    return (
      <Empty title="No questions yet">
        <p className="muted">
          Your students can ask you from inside any lesson. When they do,
          it lands here — and they see your reply on the same page they asked
          from.
        </p>
      </Empty>
    )
  }

  return (
    <div className="tview">
      <section className="tcard">
        <header className="tcard-head">
          <h2>Waiting on you ({open.length})</h2>
        </header>
        {open.length === 0 ? (
          <p className="muted small">All caught up.</p>
        ) : (
          <ul className="tqs">
            {open.map((request) => (
              <Question key={request.id} request={request} onAnswered={replace} />
            ))}
          </ul>
        )}
      </section>

      {answered.length > 0 && (
        <section className="tcard">
          <header className="tcard-head">
            <h2>Answered ({answered.length})</h2>
            <button
              type="button"
              className="linkish"
              onClick={() => setShowAnswered((v) => !v)}
            >
              {showAnswered ? 'Hide' : 'Show'}
            </button>
          </header>
          {/* Kept until the student closes it. Whether an answer helped is
              theirs to say, not the teacher's — see routers/help.py. */}
          <p className="trule">
            These stay here until the student marks them resolved.
          </p>
          {showAnswered && (
            <ul className="tqs">
              {answered.map((request) => (
                <Question key={request.id} request={request} onAnswered={replace} />
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  )
}

function Question({
  request,
  onAnswered,
}: {
  request: HelpRequest
  onAnswered: (next: HelpRequest) => void
}) {
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState<string | null>(null)
  const answered = request.status === 'answered'

  async function send(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setFailed(null)
    try {
      onAnswered(await api.answerHelp(request.id, draft.trim()))
      setDraft('')
    } catch (e) {
      setFailed(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className={answered ? 'tq is-answered' : 'tq'}>
      <header className="tq-head">
        <span className="tq-who">{request.student_name}</span>
        <span className="muted small">
          {request.exercise_title ? (
            <>
              on{' '}
              {request.exercise_slug ? (
                <Link to={`/exercise/${request.exercise_slug}/plan`}>
                  {request.exercise_title}
                </Link>
              ) : (
                request.exercise_title
              )}{' '}
              &middot;{' '}
            </>
          ) : null}
          {ago(request.created_at)}
        </span>
      </header>

      <p className="tq-body">{request.body}</p>

      {answered ? (
        <p className="tq-answer">
          <span className="tq-answer-label">You said</span>
          {request.answer}
        </p>
      ) : (
        <form className="tq-reply" onSubmit={send}>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={3}
            maxLength={4000}
            placeholder={`Answer ${request.student_name?.split(' ')[0] ?? 'them'}…`}
            aria-label="Your answer"
          />
          {failed && <p className="panel panel-error small">{failed}</p>}
          <button className="primary" disabled={busy || !draft.trim()}>
            {busy ? 'Sending…' : 'Send answer'}
          </button>
        </form>
      )}
    </li>
  )
}
