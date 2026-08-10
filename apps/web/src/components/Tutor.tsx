import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Conversation } from './Conversation'
import { api } from '../lib/api'
import { streamChat } from '../lib/stream'
import type { GeneratedLesson, LessonProposal, TutorMessage } from '../lib/types'

/**
 * The reflection tutor.
 *
 * A friendly-teacher chat at the Reflect stage. It talks about how the exercise
 * went, reads how secure the student feels, and can offer to build fresh
 * practice — either more of the whole topic or a targeted drill on something it
 * noticed.
 *
 * A DIFFERENT thing from the journal below it. The tutor sees the lesson and the
 * code they wrote; it never sees the private tried/stuck/fixed journal. That is
 * enforced on the server (services/tutor.py, routers/reflections.py) — this
 * component simply never has the journal to send.
 *
 * The chat itself is Conversation, shared with signup. What lives here is the
 * one thing only this surface does: turning an offer of practice into a real
 * exercise, verified before it is shown.
 */

/**
 * What the coach opens with, and what to press if you don't know what to say.
 *
 * Two versions, because the same words cannot serve both places this appears.
 * At the Reflect stage you have just finished something; on the Ask-for-help
 * page you are very likely stuck in the middle of it, and being congratulated
 * on "reaching the end of this one" reads as a coach who has not looked.
 *
 * The openers matter more than they look. A blank box is the hardest thing to
 * answer when you do not yet know what you do not know, and "I don't know what
 * to ask" is itself a good opener -- so it is one of them.
 */
const OPENING = {
  solved: {
    greeting:
      'Nice work reaching the end of this one. Want to talk it through? ' +
      'Tell me how it felt — what clicked, and what made you stop and think.',
    placeholder: 'Tell me how that one went…',
    starters: [
      'It worked, but I am not sure why',
      'Could I have written that more simply?',
      'What should I watch out for next time?',
    ],
  },
  stuck: {
    greeting:
      "What are you working on? Tell me where you've got to — even " +
      '"I have no idea where to start" is a fine place to begin.',
    placeholder: 'What are you stuck on?',
    starters: [
      "I don't know where to start",
      'Can you explain this in simpler words?',
      'My code runs but gives the wrong answer',
    ],
  },
}

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
  const [turns, setTurns] = useState<TutorMessage[]>([])
  const [draft, setDraft] = useState('')
  const [phase, setPhase] = useState<'idle' | 'thinking' | 'writing'>('idle')
  const [streaming, setStreaming] = useState<string | null>(null)
  const [configured, setConfigured] = useState(true)
  const [proposal, setProposal] = useState<LessonProposal | null>(null)
  const [building, setBuilding] = useState(false)
  const [built, setBuilt] = useState<GeneratedLesson | null>(null)
  const [error, setError] = useState<string | null>(null)

  const opening = solved ? OPENING.solved : OPENING.stuck

  // Load the saved conversation so it comes back exactly as it was left.
  useEffect(() => {
    let cancelled = false
    api
      .tutorHistory(exerciseId)
      .then((saved) => {
        if (!cancelled && saved.length) setTurns(saved)
      })
      .catch(() => {
        /* A failed history load must never block the chat. */
      })
    return () => {
      cancelled = true
    }
  }, [exerciseId])

  async function send(override?: string) {
    // A starter chip supplies its own text; everything else sends the box.
    const text = (override ?? draft).trim()
    if (!text || phase !== 'idle') return

    setError(null)
    setProposal(null)
    setDraft('')
    setTurns((prior) => [...prior, { role: 'user', content: text }])
    setPhase('thinking')
    setStreaming(null)

    // Held rather than committed inside onDone. The terminal line is parsed the
    // moment it arrives, which is *before* the smoothing buffer has finished
    // revealing the text it belongs to -- committing there left the finished
    // turn on screen while the streaming copy carried on drawing underneath it,
    // and the reply appeared twice. streamChat resolves after the drain, so
    // this is the first safe moment.
    let finished: Record<string, unknown> | null = null

    try {
      await streamChat(
        '/tutor/chat/stream',
        { exercise_id: exerciseId, message: text },
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
        setConfigured(payload.configured !== false)
        setProposal((payload.proposal as LessonProposal | null) ?? null)
        setTurns((prior) => [
          ...prior,
          { role: 'assistant', content: String(payload.reply ?? '') },
        ])
      }
      setStreaming(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      // Give them their words back rather than making them retype.
      setTurns((prior) => prior.slice(0, -1))
      setDraft(text)
      setStreaming(null)
    } finally {
      setPhase('idle')
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
    <Conversation
      name="Your coach"
      avatar="/agents/coach.webp"
      caption={
        solved ? 'Talk through how it went' : 'Stuck? Talk it over — no answers given away'
      }
      greeting={opening.greeting}
      turns={turns}
      streaming={streaming}
      phase={phase}
      draft={draft}
      onDraft={setDraft}
      onSend={(text) => void send(text)}
      placeholder={opening.placeholder}
      starters={opening.starters}
      disabled={!configured}
      error={error}
    >
      {proposal && !built && (
        <OfferCard proposal={proposal} building={building} onBuild={build} onDismiss={() => setProposal(null)} />
      )}
      {built && (
        <div className="cv-offer is-built">
          <p className="cv-offer-eyebrow">Built and checked</p>
          <h4>{built.title}</h4>
          <p className="muted small">
            I wrote it, then ran my own answer through the marker to be sure it
            works. It&rsquo;s yours whenever you want it.
          </p>
          <Link className="btn btn-primary" to={`/exercise/${built.slug}`}>
            Open it →
          </Link>
        </div>
      )}
    </Conversation>
  )
}

/**
 * The offer of practice.
 *
 * Presented as a thing with a name and a reason rather than a line of muted
 * text with two buttons under it. It is the one moment in the conversation
 * where the coach proposes doing work on the student's behalf, and it should
 * look like a decision worth making.
 *
 * "Not now" is as easy to reach as accepting. The model was told the tool is an
 * offer and never an action; the interface has to agree with that.
 */
function OfferCard({
  proposal,
  building,
  onBuild,
  onDismiss,
}: {
  proposal: LessonProposal
  building: boolean
  onBuild: () => void
  onDismiss: () => void
}) {
  return (
    <div className={building ? 'cv-offer is-building' : 'cv-offer'}>
      <p className="cv-offer-eyebrow">
        {proposal.scope === 'concept' ? 'A drill on one thing' : 'More of this topic'}
      </p>
      <h4>{proposal.title}</h4>
      <p className="cv-offer-focus">{proposal.focus}</p>
      {proposal.rationale && <p className="muted small">{proposal.rationale}</p>}

      {building ? (
        // The wait is 10-20 seconds, because the server writes the exercise and
        // then proves it solvable through the real marker before handing it
        // over. Saying so is better than a spinner: the delay is the feature.
        <div className="cv-building">
          <span className="cv-building-bar" aria-hidden>
            <span />
          </span>
          <span className="muted small">
            Writing it, then checking my own answer passes…
          </span>
        </div>
      ) : (
        <div className="cv-offer-actions">
          <button type="button" className="btn btn-primary" onClick={onBuild}>
            Build it for me
          </button>
          <button type="button" className="linkish" onClick={onDismiss}>
            Not now
          </button>
        </div>
      )}
    </div>
  )
}
