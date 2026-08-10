import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Conversation } from '../components/Conversation'
import { CourseBuilder } from '../components/CourseBuilder'
import { api } from '../lib/api'
import { streamChat } from '../lib/stream'
import type { OnboardingPlan, WelcomeState } from '../lib/types'

/**
 * Step three of signing up: a chat about what you'd actually like to build.
 *
 * Not a quiz and not a lesson. The mentor asks what someone is into, talks
 * through things they could make that fit, takes any idea they already have
 * seriously, and suggests a couple they might not have considered. What it
 * concludes appears beside the conversation as it goes, so the chat visibly
 * produces something rather than disappearing into a database.
 *
 * Three things this page has to get right, all about not trapping anyone in a
 * signup flow:
 *
 *  - "Start learning" is available from the first second. Nobody is held here
 *    until a model is satisfied.
 *  - No API key means no chat box at all — just a note and the way onward. A
 *    signup that dead-ends on missing configuration is worse than no third step.
 *  - The conversation is saved per turn, so closing the tab and coming back
 *    resumes it rather than starting over.
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
  const [turns, setTurns] = useState<{ role: string; content: string }[]>([])
  const [draft, setDraft] = useState('')
  const [phase, setPhase] = useState<'idle' | 'thinking' | 'writing'>('idle')
  const [streaming, setStreaming] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Set the first time the plan gains something, so the panel can announce
  // itself rather than silently filling in while you're reading the chat.
  const [planFresh, setPlanFresh] = useState(false)
  //: The project whose lessons are being written, on the way out of signup.
  const [offer, setOffer] = useState<{ id: string; title: string } | null>(null)

  useEffect(() => {
    api
      .welcomeState()
      .then((result) => {
        setState(result)
        setTurns(result.messages)
        setPlan(result.plan)
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  async function send() {
    const said = draft.trim()
    if (!said || phase !== 'idle') return

    setError(null)
    setDraft('')
    setTurns((prior) => [...prior, { role: 'user', content: said }])
    setPhase('thinking')
    setStreaming(null)

    // Held rather than committed inside onDone -- see the note in Tutor.tsx.
    // The terminal line arrives before the smoothing buffer has finished
    // drawing the text it describes, so committing there renders the reply
    // twice. streamChat resolves after the drain.
    let finished: Record<string, unknown> | null = null

    try {
      await streamChat(
        '/onboarding/welcome/chat/stream',
        { message: said },
        {
          onThinking: () => setPhase('thinking'),
          onText: (soFar) => {
            setPhase('writing')
            setStreaming(soFar)
          },
          onDone: (payload) => {
            finished = payload
          },
          onError: (message) => setError(message),
        }
      )

      if (finished) {
        const payload = finished as Record<string, unknown>
        setTurns((prior) => [
          ...prior,
          { role: 'assistant', content: String(payload.reply ?? '') },
        ])
        const next = payload.plan as OnboardingPlan | undefined
        if (next) {
          if (next.recorded && !plan?.recorded) setPlanFresh(true)
          setPlan(next)
        }
      }
      setStreaming(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setTurns((prior) => prior.slice(0, -1))
      setDraft(said)
      setStreaming(null)
    } finally {
      setPhase('idle')
    }
  }

  if (error && !state) return <p className="panel panel-error">{error}</p>
  if (!state) return <p className="muted">Loading…</p>

  const done = () => navigate('/exercises', { replace: true })

  /**
   * Finish signing up.
   *
   * With a plan recorded, the projects it described already exist, and the
   * best thing signup can do with its last moment is hand over lessons written
   * for the first of them rather than a dashboard of borrowed ones. Offered,
   * not imposed: the skip is right beside it.
   *
   * Without a plan -- they said little, or skipped straight past -- there is
   * nothing to write a course about, so this is just the way out.
   */
  async function finish() {
    if (!plan?.recorded) return done()
    try {
      const { projects } = await api.projects()
      const first = projects.find((p) => !p.has_course)
      if (!first) return done()
      setOffer({ id: first.id, title: first.title })
    } catch {
      // A dashboard is a better outcome than an error on the last screen of
      // signing up.
      done()
    }
  }

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
          A few minutes with your coach, so the lessons you get are about things
          you actually care about. Say as much or as little as you like.
        </p>
      </header>

      <div className="welcome-chat-grid">
        <Conversation
          name="Your coach"
          avatar="/agents/coach.webp"
          caption="Getting to know you"
          greeting={state.greeting}
          turns={turns}
          streaming={streaming}
          phase={phase}
          draft={draft}
          onDraft={setDraft}
          onSend={() => void send()}
          placeholder="Tell me a bit about yourself…"
          error={error}
        />

        <PlanPanel plan={plan} fresh={planFresh} writing={phase !== 'idle'} />
      </div>

      {/* Always available, from the first second. Nobody is kept in a signup
          flow until a model decides it has heard enough. */}
      <div className="welcome-actions">
        <button className="primary" onClick={() => void finish()}>
          {plan?.recorded ? 'Start learning' : "I'm ready to start"}
        </button>
        <span className="muted small">
          You can carry on this conversation with your coach inside any lesson.
        </span>
      </div>

      {/* The last thing signup does, and the first thing the dashboard should
          have on it: lessons written for the project they just described.
          Offered rather than imposed -- it takes a couple of minutes, and
          somebody who wants to start right now should be able to. */}
      {offer && (
        <div className="welcome-course">
          <CourseBuilder
            projectId={offer.id}
            projectTitle={offer.title}
            onFinished={done}
          />
          <button type="button" className="linkish" onClick={done}>
            Skip — I&rsquo;ll start with the standard lessons
          </button>
        </div>
      )}
    </div>
  )
}

/**
 * What the conversation has worked out so far.
 *
 * The reason the chat is worth having: it visibly produces something. Before,
 * this was a tall box with a placeholder at the top and a footnote at the
 * bottom and a great deal of nothing between them — which made the panel look
 * broken until the model happened to call its tool.
 *
 * Now it shows the shape of what it will hold, so the empty state reads as
 * "not yet" rather than "nothing here".
 */
function PlanPanel({
  plan,
  fresh,
  writing,
}: {
  plan: OnboardingPlan | null
  fresh: boolean
  writing: boolean
}) {
  const recorded = Boolean(plan?.recorded)

  return (
    <aside className={recorded ? 'wc-plan is-live' : 'wc-plan'} aria-live="polite">
      <div className="wc-plan-head">
        <h2>Your plan</h2>
        {recorded && fresh && <span className="wc-plan-new">Updated</span>}
      </div>

      {!recorded ? (
        <div className="wc-plan-empty">
          <p className="muted small">
            {writing
              ? 'Listening…'
              : 'As you talk, this fills in — the topics worth starting with, and projects that fit what you are into.'}
          </p>
          {/* The shape of what is coming, so an empty panel reads as "not yet"
              rather than as a box that failed to load. */}
          <ul className="wc-ghost" aria-hidden>
            <li />
            <li />
            <li />
          </ul>
        </div>
      ) : (
        <>
          {plan?.interests && <p className="wc-interests">{plan.interests}</p>}

          {plan!.topics.length > 0 && (
            <section>
              <h3>Start with</h3>
              <ul className="wc-topics">
                {plan!.topics.map((topic) => (
                  <li key={topic}>{TOPIC_LABELS[topic] ?? topic}</li>
                ))}
              </ul>
            </section>
          )}

          {plan!.projects.length > 0 && (
            <section>
              <h3>Things you could build</h3>
              <ul className="wc-projects">
                {plan!.projects.map((project) => (
                  <li key={project.title}>
                    <strong>{project.title}</strong>
                    <span>{project.blurb}</span>
                    {project.topics.length > 0 && (
                      <span className="wc-project-topics">
                        {project.topics.map((t) => TOPIC_LABELS[t] ?? t).join(' · ')}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      <p className="wc-plan-foot muted small">
        Saved to your account, and yours to change later.
      </p>
    </aside>
  )
}
