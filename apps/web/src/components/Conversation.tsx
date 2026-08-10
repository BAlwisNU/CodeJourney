import { useEffect, useRef } from 'react'

import { Markdown } from './Markdown'

/**
 * Every conversation with a model, drawn the same way.
 *
 * There were two of these and they were different in ways nobody chose: the
 * reflect tutor had an auto-growing textarea, Enter-to-send and an animated
 * waiting state; the signup chat had a single-line input, a Send button and the
 * word "Thinking…". Same act, two qualities of it. This is the one both use.
 *
 * What makes it feel like talking to someone rather than filling in a form:
 *
 *  - **Somebody is there.** A named face, not a monogram — the platform already
 *    has four illustrated coaches sitting unused in public/agents.
 *  - **Waiting says what is happening.** "Thinking" while the model reasons,
 *    then words. Both are real signals from the API, not a timer pretending.
 *  - **Text arrives as it is written** and is revealed at a readable rate; see
 *    lib/stream for why the smoothing is adaptive rather than a fixed speed.
 *  - **The composer grows with what you type**, sends on Enter, and never
 *    disappears or disables itself mid-thought — losing a half-written sentence
 *    because a reply landed is the rudest thing a chat can do.
 */

export type Turn = { role: string; content: string }

export function Conversation({
  turns,
  greeting,
  streaming,
  phase,
  draft,
  onDraft,
  onSend,
  placeholder,
  name,
  avatar,
  caption,
  disabled,
  error,
  children,
}: {
  turns: Turn[]
  /** Shown as the first assistant turn. Local, never sent — the model didn't
   *  say it, so it doesn't belong in the history. */
  greeting: string
  /** The reply as it is being written, or null between turns. */
  streaming: string | null
  phase: 'idle' | 'thinking' | 'writing'
  draft: string
  onDraft: (value: string) => void
  onSend: () => void
  placeholder: string
  name: string
  avatar: string
  caption?: string
  /** True when there's no API key: the composer is replaced by a note. */
  disabled?: boolean
  error?: string | null
  /** Offers and outcomes that belong at the end of the thread. */
  children?: React.ReactNode
}) {
  const endRef = useRef<HTMLDivElement | null>(null)
  const boxRef = useRef<HTMLTextAreaElement | null>(null)

  // Follow the newest turn, including while it is being written. `block: nearest`
  // keeps the page still when the thread is already in view — a chat that yanks
  // the whole document on every frame is unusable.
  useEffect(() => {
    if (turns.length || streaming) {
      endRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [turns.length, streaming, phase])

  function grow(el: HTMLTextAreaElement) {
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  }

  return (
    <section className="cv" aria-label={`Conversation with ${name}`}>
      <header className="cv-head">
        <img className="cv-face" src={avatar} alt="" width={36} height={36} />
        <div>
          <strong>{name}</strong>
          {caption && <span className="muted small">{caption}</span>}
        </div>
        {phase !== 'idle' && (
          <span className="cv-status" role="status">
            <span className="cv-pulse" aria-hidden />
            {phase === 'thinking' ? 'Thinking' : 'Writing'}
          </span>
        )}
      </header>

      <div className="cv-thread">
        <Bubble role="assistant" avatar={avatar}>
          <Markdown source={greeting} />
        </Bubble>

        {turns.map((turn, i) => (
          <Bubble key={i} role={turn.role} avatar={avatar}>
            {turn.role === 'user' ? (
              <p>{turn.content}</p>
            ) : (
              <Markdown source={turn.content} />
            )}
          </Bubble>
        ))}

        {/* One element for both waiting states, so the transition from thinking
            to the first words is a change of content rather than one box being
            swapped for another. */}
        {(phase !== 'idle' || streaming) && (
          <Bubble role="assistant" avatar={avatar} live>
            {streaming ? (
              // The caret is drawn by CSS on the last paragraph rather than as
              // an element here: a sibling span after a block <p> always lands
              // on its own line, which reads as the coach having pressed enter.
              <Markdown source={streaming} />
            ) : (
              <span className="cv-dots" aria-label="Thinking">
                <i />
                <i />
                <i />
              </span>
            )}
          </Bubble>
        )}

        {children}
        {error && <p className="cv-error">{error}</p>}
        <div ref={endRef} />
      </div>

      {disabled ? (
        <p className="cv-off muted small">
          {name} isn&rsquo;t switched on for this server yet.
        </p>
      ) : (
        <form
          className="cv-composer"
          onSubmit={(event) => {
            event.preventDefault()
            onSend()
          }}
        >
          <textarea
            ref={boxRef}
            rows={1}
            value={draft}
            onChange={(event) => {
              onDraft(event.target.value)
              grow(event.currentTarget)
            }}
            onKeyDown={(event) => {
              // Enter sends, Shift+Enter breaks the line — what every chat does,
              // and what anyone typing here will try first.
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                onSend()
                if (boxRef.current) {
                  boxRef.current.style.height = 'auto'
                }
              }
            }}
            placeholder={placeholder}
            maxLength={4000}
            aria-label="Your message"
          />
          {/* Deliberately not disabled while a reply streams. You should be able
              to start typing your next thought the moment you have it, and the
              send button is the only thing that waits. */}
          <button
            type="submit"
            className="cv-send"
            disabled={phase !== 'idle' || !draft.trim()}
            aria-label="Send"
          >
            <svg viewBox="0 0 20 20" width="17" height="17" aria-hidden>
              <path
                d="M10 16V4M10 4l-5 5M10 4l5 5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </form>
      )}
    </section>
  )
}

function Bubble({
  role,
  avatar,
  live,
  children,
}: {
  role: string
  avatar: string
  live?: boolean
  children: React.ReactNode
}) {
  const mine = role === 'user'
  return (
    <article className={mine ? 'cv-turn is-mine' : 'cv-turn'}>
      {!mine && <img className="cv-turn-face" src={avatar} alt="" width={26} height={26} />}
      <div className={live ? 'cv-bubble is-live' : 'cv-bubble'}>{children}</div>
    </article>
  )
}
