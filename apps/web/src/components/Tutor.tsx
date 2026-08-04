import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { GeneratedLesson, LessonProposal, TutorMessage } from '../lib/types'
import { Markdown } from './Markdown'

/**
 * The reflection tutor.
 *
 * A friendly-teacher chat at the Reflect stage. It talks with the student about
 * how the exercise went, reads how secure they feel, and can offer to build a
 * fresh practice exercise -- either more of the whole topic or a targeted drill
 * on something it noticed.
 *
 * This is a DIFFERENT thing from the journal below it. The tutor sees the lesson
 * and the code the student wrote; it never sees the private tried/stuck/fixed
 * journal. That boundary is enforced on the server (apps/api/app/services/tutor.py,
 * routers/reflections.py) -- this component simply never has the journal to send.
 *
 * The greeting is shown locally and costs nothing; the model is only called when
 * the student actually says something.
 */

const GREETING =
  "Nice work reaching the end of this one. Want to talk it through? " +
  "Tell me how it felt — what clicked, and what made you stop and think."

export function Tutor({
  exerciseId,
  solved,
  onLessonCreated,
}: {
  exerciseId: string
  solved: boolean
  /** Fired when a branch is built here, so the parent page can link to it. */
  onLessonCreated?: (lesson: GeneratedLesson) => void
}) {
  // Only the real exchange with the model. The greeting above is local and is
  // never sent -- the model didn't say it, so it doesn't belong in the history.
  const [messages, setMessages] = useState<TutorMessage[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [configured, setConfigured] = useState(true)
  const [proposal, setProposal] = useState<LessonProposal | null>(null)
  const [building, setBuilding] = useState(false)
  const [built, setBuilt] = useState<GeneratedLesson | null>(null)
  const [error, setError] = useState<string | null>(null)
  const scroller = useRef<HTMLDivElement | null>(null)

  // Load the saved conversation so it comes back exactly as it was left. If
  // there's history, open the panel on arrival rather than making them hunt for
  // it -- same courtesy the journal extends to a started entry.
  useEffect(() => {
    let cancelled = false
    api
      .tutorHistory(exerciseId)
      .then((saved) => {
        if (cancelled || saved.length === 0) return
        setMessages(saved)
      })
      .catch(() => {
        /* a failed history load must never block the chat */
      })
    return () => {
      cancelled = true
    }
  }, [exerciseId])

  function scrollToEnd() {
    // After the DOM paints the new bubble, keep the latest turn in view.
    requestAnimationFrame(() => {
      const el = scroller.current
      if (el) el.scrollTop = el.scrollHeight
    })
  }

  async function send() {
    const text = draft.trim()
    if (!text || busy) return
    setError(null)
    setProposal(null)
    const next = [...messages, { role: 'user' as const, content: text }]
    setMessages(next)
    setDraft('')
    setBusy(true)
    scrollToEnd()
    try {
      const res = await api.tutorChat(exerciseId, text)
      setConfigured(res.configured)
      setMessages([...next, { role: 'assistant', content: res.reply }])
      setProposal(res.proposal)
      scrollToEnd()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      // Roll the unsent turn back so they can retry without losing their words.
      setMessages(messages)
      setDraft(text)
    } finally {
      setBusy(false)
    }
  }

  async function build() {
    if (!proposal || building) return
    setBuilding(true)
    setError(null)
    try {
      const lesson = await api.generateLesson(proposal, exerciseId)
      setBuilt(lesson)
      setProposal(null)
      onLessonCreated?.(lesson)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBuilding(false)
    }
  }

  return (
    <section className="chat" aria-label="Tutor conversation">
      <header className="chat-head">
        <span className="chat-avatar" aria-hidden>
          {'{ }'}
        </span>
        <div>
          <strong>Your tutor</strong>
          <span className="muted small">
            {solved
              ? 'Talk through how it went'
              : 'Stuck? Talk it over — no answers given away'}
          </span>
        </div>
      </header>

      <div className="chat-thread" ref={scroller}>
        <article className="chat-turn assistant">
          <span className="chat-who" aria-hidden>
            {'{ }'}
          </span>
          <div className="chat-bubble">
            <Markdown source={GREETING} />
          </div>
        </article>

        {messages.map((m, i) => (
          <article key={i} className={`chat-turn ${m.role === 'user' ? 'user' : 'assistant'}`}>
            {m.role === 'assistant' && (
              <span className="chat-who" aria-hidden>
                {'{ }'}
              </span>
            )}
            <div className="chat-bubble">
              {m.role === 'user' ? <p>{m.content}</p> : <Markdown source={m.content} />}
            </div>
          </article>
        ))}

        {busy && (
          <article className="chat-turn assistant" aria-live="polite">
            <span className="chat-who" aria-hidden>
              {'{ }'}
            </span>
            <div className="chat-bubble chat-thinking">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </article>
        )}

        {proposal && !built && (
          <div className="chat-offer">
            <p className="chat-offer-title">
              {proposal.scope === 'concept'
                ? 'Want a targeted practice exercise?'
                : 'Want more practice on this topic?'}
            </p>
            <p className="muted small">
              <strong>{proposal.title}</strong> — {proposal.focus}
            </p>
            <div className="actions">
              <button type="button" className="primary" onClick={build} disabled={building}>
                {building ? 'Building it…' : 'Build it for me'}
              </button>
              <button
                type="button"
                className="link"
                onClick={() => setProposal(null)}
                disabled={building}
              >
                Not now
              </button>
            </div>
            {building && (
              <p className="muted small">
                Writing the exercise and checking it&rsquo;s solvable…
              </p>
            )}
          </div>
        )}

        {built && (
          <div className="chat-offer">
            <p>
              Done — I built <strong>{built.title}</strong> for you and checked it works.
            </p>
            <Link className="primary button-link" to={`/exercise/${built.slug}`}>
              Open the practice exercise →
            </Link>
          </div>
        )}

        {error && <p className="panel panel-error small">{error}</p>}
      </div>

      {configured ? (
        <form
          className="chat-composer"
          onSubmit={(e) => {
            e.preventDefault()
            send()
          }}
        >
          <textarea
            rows={1}
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value)
              // Grow with the text, up to the cap in the stylesheet. A fixed
              // two-row box makes anything longer than a sentence feel like
              // writing through a letterbox.
              const el = e.currentTarget
              el.style.height = 'auto'
              el.style.height = `${Math.min(el.scrollHeight, 200)}px`
            }}
            onKeyDown={(e) => {
              // Enter sends; Shift+Enter for a newline, like every chat.
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
            placeholder="Type how it went…"
            disabled={busy}
          />
          <button
            type="submit"
            className="chat-send"
            disabled={busy || !draft.trim()}
            aria-label="Send"
          >
            ↑
          </button>
        </form>
      ) : (
        <p className="muted small chat-off">
          The tutor isn&rsquo;t switched on yet, but your journal below is always
          here.
        </p>
      )}
    </section>
  )
}
