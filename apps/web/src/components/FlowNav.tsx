import { Link, useNavigate } from 'react-router-dom'

import { endDemo, useDemoKind } from '../lib/demo'

/**
 * Connect → Read & Watch → Quiz → Create → Test and improve → Reflect.
 *
 * Visible on every stage so the student always knows where they are in the
 * cycle and that reflection is a real step rather than an optional extra tacked
 * on the end.
 *
 * Create and Test share a page — you write and run in the same editor, and
 * splitting them would mean navigating away from your code to see whether it
 * worked. They're shown as one step with both labels.
 */

export type Stage = 'connect' | 'plan' | 'quiz' | 'create' | 'reflect'

// Order is the numbering -- see the note where flow-n is rendered.
const STAGES: { key: Stage; label: string; sub: string }[] = [
  { key: 'connect', label: 'Connect', sub: 'Pick a project' },
  // The stage key stays 'plan' -- it is the route (/exercise/:slug/plan) and
  // the value stored against every sitting. Only the label a learner reads
  // changed: "Read & Watch" says what you actually do here, where "Plan"
  // described the teaching model rather than the activity.
  { key: 'plan', label: 'Read & Watch', sub: 'Lesson and warm-up' },
  { key: 'quiz', label: 'Quiz', sub: 'Check what stuck' },
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
  const navigate = useNavigate()
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
                : stage.key === 'create'
                  ? `/exercise/${slug}`
                  : `/exercise/${slug}/${stage.key}`

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

        {/* A way out, always, and marked with an arrow rather than a number
            because it is not a stage of the cycle.
            
            The stages describe where you are inside a lesson; none of them says
            "I'm done here for now". Connect happens to lead to the dashboard,
            but "Pick a project" does not read as an exit, and a demo has no
            Connect at all -- so each gets a labelled way out, to the place that
            makes sense for them. */}
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
