import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Markdown } from '../components/Markdown'
import { api } from '../lib/api'
import type { OnboardingPlan, WelcomeState } from '../lib/types'

/**
 * Step three of signing up: a chat about what you'd actually like to build.
 *
 * Not a quiz and not a lesson. The mentor asks what someone is into, talks
 * through things they could make that fit, takes any idea they already have
 * seriously, and suggests a couple they might not have considered. What it
 * concludes appears in the panel beside the conversation as it goes, so the
 * chat visibly produces something rather than disappearing into a database.
 *
 * Three things this page has to get right, all of them about not trapping
 * anyone in a signup flow:
 *
 *  - "Start learning" is always available, from the first second. Nobody is
 *    held here until a model is satisfied.
 *  - If the server has no API key, there is no chat box at all -- just a note
 *    and the way onward. A signup that dead-ends on missing configuration is
 *    worse than no third step.
 *  - The conversation is saved server-side per turn, so closing the tab and
 *    coming back to /welcome/chat resumes it rather than starting over.
 */

const TOPIC_LABELS: Record<string, string> = {
  lists: 'Lists',
  dicts: 'Dictionaries',
  loops: 'Loops',
  strings: 'Strings',
  functions: 'Functions',
  file_io: 'Files',
}

export function WelcomeChatPage() {
  const navigate = useNavigate()
  const [state, setState] = useState<WelcomeState | null>(null)
  const [plan, setPlan] = useState<OnboardingPlan | null>(null)
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api
      .welcomeState()
      .then((result) => {
        setState(result)
        setMessages(result.messages)
        setPlan(result.plan)
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  // Keep the newest turn in view, but only once there is a conversation --
  // scrolling on first paint would yank the page for no reason.
  useEffect(() => {
    if (messages.length) endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, busy])

  async function send(event: React.FormEvent) {
    event.preventDefault()
    const said = draft.trim()
    if (!said || busy) return

    // Shown immediately. Waiting for the server to echo it back makes typing
    // feel laggy in the one place we want the conversation to feel easy.
    setMessages((prior) => [...prior, { role: 'user', content: said }])
    setDraft('')
    setBusy(true)
    setError(null)
    try {
      const result = await api.welcomeChat(said)
      setMessages((prior) => [...prior, { role: 'assistant', content: result.reply }])
      setPlan(result.plan)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  if (error && !state) return <p className="panel panel-error">{error}</p>
  if (!state) return <p className="muted">Loading…</p>

  const done = () => navigate('/exercises', { replace: true })

  if (!state.available) {
    return (
      <div className="welcome">
        <p className="eyebrow">Step 3 of 3</p>
        <h1>You&rsquo;re all set</h1>
        <p className="muted">
          There&rsquo;s normally a chat here about what you&rsquo;d like to
          build, but it isn&rsquo;t switched on for this server. Nothing else is
          affected — everything is ready for you.
        </p>
        <div className="welcome-actions">
          <button className="primary" onClick={done}>
            Start learning
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="welcome-chat">
      <header>
        <p className="eyebrow">Step 3 of 3</p>
        <h1>What would you like to build?</h1>
        <p className="muted">
          A quick chat, so the lessons and examples you get are about things you
          actually care about. Say as much or as little as you like.
        </p>
      </header>

      <div className="welcome-chat-grid">
        <section className="wc-thread" aria-label="Conversation">
          <article className="wc-msg wc-assistant">
            <Markdown source={state.greeting} />
          </article>

          {messages.map((message, index) => (
            <article
              key={index}
              className={
                message.role === 'user' ? 'wc-msg wc-user' : 'wc-msg wc-assistant'
              }
            >
              {message.role === 'user' ? (
                <p>{message.content}</p>
              ) : (
                <Markdown source={message.content} />
              )}
            </article>
          ))}

          {busy && (
            <p className="wc-thinking muted small" role="status">
              Thinking…
            </p>
          )}
          {error && <p className="panel panel-error small">{error}</p>}
          <div ref={endRef} />

          <form className="wc-composer" onSubmit={send}>
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Tell them a bit about yourself…"
              maxLength={4000}
              disabled={busy}
              aria-label="Your message"
              autoFocus
            />
            <button className="primary" disabled={busy || !draft.trim()}>
              Send
            </button>
          </form>
        </section>

        <aside className="wc-plan" aria-label="What we've worked out">
          <h2>Your plan so far</h2>

          {!plan?.recorded ? (
            <p className="muted small">
              As you chat, the ideas you settle on will appear here — topics
              worth starting with, and projects that fit them.
            </p>
          ) : (
            <>
              {plan.interests && <p className="wc-interests">{plan.interests}</p>}

              {plan.topics.length > 0 && (
                <>
                  <h3>Good places to start</h3>
                  <ul className="wc-topics">
                    {plan.topics.map((topic) => (
                      <li key={topic}>{TOPIC_LABELS[topic] ?? topic}</li>
                    ))}
                  </ul>
                </>
              )}

              {plan.projects.length > 0 && (
                <>
                  <h3>Things you could build</h3>
                  <ul className="wc-projects">
                    {plan.projects.map((project) => (
                      <li key={project.title}>
                        <strong>{project.title}</strong>
                        <span>{project.blurb}</span>
                        {project.topics.length > 0 && (
                          <span className="wc-project-topics">
                            {project.topics
                              .map((t) => TOPIC_LABELS[t] ?? t)
                              .join(' · ')}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          )}

          <p className="muted small">
            Saved to your account. You can see it any time on your account page.
          </p>
        </aside>
      </div>

      {/* Always available, from the first second. Nobody is kept in a signup
          flow until a model decides it has heard enough. */}
      <div className="welcome-actions">
        <button className="primary" onClick={done}>
          {plan?.recorded ? 'Start learning' : "I'm ready to start"}
        </button>
        <span className="muted small">
          You can carry on this conversation with the tutor inside any lesson.
        </span>
      </div>
    </div>
  )
}
