import { Link } from 'react-router-dom'

import { useDemoKind } from '../lib/demo'

/**
 * Connect → Plan → Create → Test and improve → Reflect.
 *
 * Visible on every stage so the student always knows where they are in the
 * cycle and that reflection is a real step rather than an optional extra tacked
 * on the end.
 *
 * Create and Test share a page — you write and run in the same editor, and
 * splitting them would mean navigating away from your code to see whether it
 * worked. They're shown as one step with both labels.
 */

export type Stage = 'connect' | 'plan' | 'create' | 'reflect'

// Order is the numbering -- see the note where flow-n is rendered.
const STAGES: { key: Stage; label: string; sub: string }[] = [
  { key: 'connect', label: 'Connect', sub: 'Pick a project' },
  { key: 'plan', label: 'Plan', sub: 'Lesson, quiz, warm-up' },
  { key: 'create', label: 'Create & test', sub: 'Write it, run it, fix it' },
  { key: 'reflect', label: 'Reflect', sub: 'What you learned' },
]

export function FlowNav({
  current,
  slug,
}: {
  current: Stage
  /** Omitted on Connect, where no project has been chosen yet. */
  slug?: string
}) {
  // Someone who arrived via "Demo Lesson" has no dashboard behind them -- they
  // never picked a project, they were dropped straight into one. Connect is
  // dropped from their flow entirely rather than shown greyed out: a visible
  // step you cannot take is a worse answer than a flow that simply starts
  // where you started. The account demo keeps it, because wandering around is
  // the entire point of that one.
  const lessonDemo = useDemoKind() === 'lesson'
  const stages = lessonDemo
    ? STAGES.filter((stage) => stage.key !== 'connect')
    : STAGES

  return (
    <nav className="flow" aria-label="Where you are">
      <ol>
        {stages.map((stage, index) => {
          const active = stage.key === current
          const target =
            stage.key === 'connect'
              ? '/exercises'
              : !slug
                ? null
                : stage.key === 'plan'
                  ? `/exercise/${slug}/plan`
                  : stage.key === 'reflect'
                    ? `/exercise/${slug}/reflect`
                    : `/exercise/${slug}`

          const body = (
            <>
              {/* Numbered by position, not by the stage's own number. With
                  Connect removed the sequence has to read 1-2-3; leaving a
                  gap where step 1 was looks like something failed to load. */}
              <span className="flow-n">{index + 1}</span>
              <span className="flow-text">
                <strong>{stage.label}</strong>
                <span className="flow-sub">{stage.sub}</span>
              </span>
            </>
          )

          return (
            <li key={stage.key} className={active ? 'flow-step on' : 'flow-step'}>
              {target && !active ? (
                <Link to={target}>{body}</Link>
              ) : (
                <span aria-current={active ? 'step' : undefined}>{body}</span>
              )}
            </li>
          )
        })}

        {/* The lesson demo's way out. Connect is gone for these visitors, so
            without this the flow has no exit at all -- and the place to send
            them is the page they came from, not a dashboard belonging to an
            account they never made. Marked with an arrow rather than a number
            because it is not a stage of the cycle. */}
        {lessonDemo && (
          <li className="flow-step flow-exit">
            <Link to="/">
              <span className="flow-n" aria-hidden>
                &larr;
              </span>
              <span className="flow-text">
                <strong>Leave the demo</strong>
                <span className="flow-sub">Back to the home page</span>
              </span>
            </Link>
          </li>
        )}
      </ol>
    </nav>
  )
}
