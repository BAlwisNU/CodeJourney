import { Link, useNavigate } from 'react-router-dom'

import { endDemo, useDemoKind } from '../lib/demo'

/**
 * Read & Watch → Quiz → Create → Test and improve → Reflect.
 *
 * Visible on every stage so the student always knows where they are in the
 * cycle and that reflection is a real step rather than an optional extra tacked
 * on the end.
 *
 * Create and Test share a page — you write and run in the same editor, and
 * splitting them would mean navigating away from your code to see whether it
 * worked. They're shown as one step with both labels.
 */

export type Stage = 'plan' | 'quiz' | 'create' | 'reflect'

// Order is the numbering -- see the note where flow-n is rendered.
//
// There is no Connect step. It meant "pick a project", which is something you
// do before a lesson rather than inside one -- by the time this nav is on
// screen the project is already chosen, so the step was never the current one
// on any page. Getting back to the list is what the exit at the end is for.
const STAGES: { key: Stage; label: string; sub: string }[] = [
  // The stage key stays 'plan' -- it is the route (/exercise/:slug/plan) and
  // the value stored against every sitting. Only the label a learner reads
  // changed: "Read & Watch" says what you actually do here, where "Plan"
  // described the teaching model rather than the activity.
  { key: 'plan', label: 'Read & Watch', sub: 'Lesson and warm-up' },
  { key: 'quiz', label: 'Quiz', sub: 'Check what stuck' },
  // The stage key stays 'create' -- it is the value stored against every
  // sitting, and the label is the only part a learner reads.
  { key: 'create', label: 'Code & test', sub: 'Write it, run it, fix it' },
  { key: 'reflect', label: 'Reflect', sub: 'What you learned' },
]

export function FlowNav({
  current,
  slug,
}: {
  current: Stage
  /** Every stage is inside one exercise, so this is always known in practice. */
  slug?: string
}) {
  // Only still needed to decide which way out to offer: someone who arrived
  // via "Demo Lesson" is not signed in and has nothing to go back to.
  const navigate = useNavigate()
  const lessonDemo = useDemoKind() === 'lesson'
  const stages = STAGES

  return (
    <nav className="flow" aria-label="Where you are">
      <ol>
        {stages.map((stage, index) => {
          const active = stage.key === current
          const target = !slug
            ? null
            : stage.key === 'create'
              ? `/exercise/${slug}`
              : `/exercise/${slug}/${stage.key}`

          const body = (
            <>
              {/* Numbered by position rather than by any fixed number, so the
                  sequence always reads 1-2-3 however the list changes. */}
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

        {/* A way out, always, and marked with an arrow rather than a number
            because it is not a stage of the cycle.

            The stages describe where you are inside a lesson; none of them says
            "I'm done here for now". So each kind of visitor gets a labelled way
            out, to the place that makes sense for them. */}
        {lessonDemo ? (
          <li className="flow-step flow-exit">
            {/* A button, not a link: leaving throws the throwaway account away
                as well as navigating. Trying a sample lesson is not signing in,
                so nobody should arrive back at the home page apparently logged
                into an account they never made. */}
            <button
              type="button"
              onClick={() => {
                endDemo()
                navigate('/', { replace: true })
              }}
            >
              <span className="flow-n" aria-hidden>
                &larr;
              </span>
              <span className="flow-text">
                <strong>Leave the demo</strong>
                <span className="flow-sub">Back to the home page</span>
              </span>
            </button>
          </li>
        ) : (
          <li className="flow-step flow-exit">
            {/* A plain link, unlike the demo's button: a real learner stays
                signed in, and their work is already saved. Nothing to discard,
                nothing to warn about. */}
            <Link to="/exercises">
              <span className="flow-n" aria-hidden>
                &larr;
              </span>
              <span className="flow-text">
                <strong>Leave the lesson</strong>
                <span className="flow-sub">Back to your lessons</span>
              </span>
            </Link>
          </li>
        )}
      </ol>
    </nav>
  )
}
