import { useEffect, useRef, useState } from 'react'

import { usePrefersReducedMotion } from '../lib/motion'

/**
 * The coach, as four tabs that revolve on their own.
 *
 * The section used to be four cards in a grid, which said everything at once
 * and so emphasised nothing. As tabs it introduces one part at a time, in the
 * order you actually meet them, and the opening tab shows all four together so
 * nobody has to click to find out what is behind the others.
 *
 * It rotates by itself because this is a landing page: most people will not
 * click anything, and a tab strip nobody touches shows one quarter of the
 * content. Any interaction stops the rotation for good -- once you have chosen
 * a tab, having it slide away underneath you is the rudest thing the component
 * could do. Hover and focus pause it for the same reason.
 *
 * Artwork is optional. Missing files fall back to a monogram, so the section
 * is complete before the illustrations exist and improves when they land
 * rather than breaking until then.
 */

const ROTATE_MS = 7000

export type Agent = {
  id: string
  /** Short label for the tab. */
  name: string
  /** When in the journey you meet them. */
  when: string
  title: string
  /** Their own account of what they do. */
  say: string
  /** Bare `r,g,b`, so the tab can tint without a second variable. */
  tint: string
  art: string
}

export const AGENTS: Agent[] = [
  {
    id: 'scout',
    name: 'Scout',
    when: 'When you sign up',
    title: 'I ask what you actually want to build',
    say: 'A conversation, not a form. It ends with a plan — the topics to learn, and projects worth building with them. Yours, not a default syllabus.',
    tint: '124, 156, 255',
    art: '/agents/scout.webp',
  },
  {
    id: 'coach',
    name: 'Coach',
    when: 'While you are learning',
    title: 'I talk like a friend who happens to code',
    say: 'Short turns, one question at a time, never a lecture. What I am working out is not whether your tests passed — it is whether you could do it again tomorrow.',
    tint: '167, 139, 250',
    art: '/agents/coach.webp',
  },
  {
    id: 'forge',
    name: 'Forge',
    when: 'When you want more',
    title: 'I build practice around your goals',
    say: 'When something has not landed, I write you a new exercise on exactly that — and solve it myself, through the grader that marks your work, before you see it.',
    tint: '52, 211, 153',
    art: '/agents/forge.webp',
  },
  {
    id: 'keeper',
    name: 'Keeper',
    when: 'Whenever you like',
    title: 'You decide what I know about you',
    say: 'Your goals live in your account, in your words. Rewrite them whenever and we all work from the new ones.',
    tint: '34, 211, 238',
    art: '/agents/keeper.webp',
  },
]

/** The artwork, or a monogram if it is not there yet. */
function Portrait({
  src,
  alt,
  initial,
  tint,
  className,
}: {
  src: string
  alt: string
  initial: string
  tint: string
  className: string
}) {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <div
        className={`${className} agent-mono`}
        style={{ '--mono': tint } as React.CSSProperties}
        aria-hidden
      >
        {initial}
      </div>
    )
  }
  return (
    <img
      className={className}
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  )
}

export function AgentTabs() {
  // -1 is the "all four" tab, which is where everyone starts.
  const [at, setAt] = useState(-1)
  const [stopped, setStopped] = useState(false)
  const [paused, setPaused] = useState(false)
  const reduced = usePrefersReducedMotion()
  const region = useRef<HTMLDivElement>(null)

  const rotating = !stopped && !paused && !reduced

  useEffect(() => {
    if (!rotating) return
    const timer = setTimeout(
      () => setAt((n) => (n + 1 >= AGENTS.length ? -1 : n + 1)),
      ROTATE_MS
    )
    return () => clearTimeout(timer)
  }, [rotating, at])

  /** Any deliberate choice ends the rotation -- see the note at the top. */
  const choose = (next: number) => {
    setStopped(true)
    setAt(next)
  }

  const tabs = [{ id: 'all', name: 'Meet all four' }, ...AGENTS]
  const active = at < 0 ? 'all' : AGENTS[at].id

  return (
    <div
      className="agent-tabs"
      ref={region}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={() => setPaused(false)}
    >
      <div className="agent-tablist" role="tablist" aria-label="Meet your coach">
        {tabs.map((tab, i) => {
          const index = i - 1
          const on = tab.id === active
          return (
            <button
              key={tab.id}
              role="tab"
              type="button"
              id={`agent-tab-${tab.id}`}
              aria-selected={on}
              aria-controls={`agent-panel-${tab.id}`}
              className={on ? 'agent-tab is-on' : 'agent-tab'}
              onClick={() => choose(index)}
            >
              {tab.name}
              {/* The bar under the live tab drains as its turn runs out, so the
                  rotation is something you can see coming rather than a jump. */}
              {on && rotating && (
                <span className="agent-tick" key={at} aria-hidden />
              )}
            </button>
          )
        })}
      </div>

      {at < 0 ? (
        <div
          className="agent-panel agent-all"
          role="tabpanel"
          id="agent-panel-all"
          aria-labelledby="agent-tab-all"
        >
          <Portrait
            className="agent-group"
            src="/agents/all.webp"
            alt="The four CodeJourney coaches"
            initial="4"
            tint="124, 156, 255"
          />
          <ul className="agent-mini">
            {AGENTS.map((agent, i) => (
              <li key={agent.id}>
                <button type="button" onClick={() => choose(i)}>
                  <Portrait
                    className="agent-face"
                    src={agent.art}
                    alt=""
                    initial={agent.name[0]}
                    tint={agent.tint}
                  />
                  <span className="agent-mini-text">
                    <strong>{agent.name}</strong>
                    <span>{agent.title.replace(/^I /, '').replace(/^You /, 'You ')}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        (() => {
          const agent = AGENTS[at]
          return (
            <div
              className="agent-panel agent-one"
              role="tabpanel"
              id={`agent-panel-${agent.id}`}
              aria-labelledby={`agent-tab-${agent.id}`}
              // Keyed so the panel animates in on each change rather than the
              // text swapping under a static frame.
              key={agent.id}
              style={{ '--tint': agent.tint } as React.CSSProperties}
            >
              <Portrait
                className="agent-hero"
                src={agent.art}
                alt={agent.name}
                initial={agent.name[0]}
                tint={agent.tint}
              />
              <div className="agent-said">
                <span className="agent-when">{agent.when}</span>
                <h3>{agent.title}</h3>
                <p>{agent.say}</p>
                <p className="agent-sign">— {agent.name}</p>
              </div>
            </div>
          )
        })()
      )}
    </div>
  )
}
