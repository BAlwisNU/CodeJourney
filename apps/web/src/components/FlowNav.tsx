import { Link } from 'react-router-dom'

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

const STAGES: { key: Stage; n: number; label: string; sub: string }[] = [
  { key: 'connect', n: 1, label: 'Connect', sub: 'Pick a project' },
  { key: 'plan', n: 2, label: 'Plan', sub: 'Lesson, quiz, warm-up' },
  { key: 'create', n: 3, label: 'Create & test', sub: 'Write it, run it, fix it' },
  { key: 'reflect', n: 4, label: 'Reflect', sub: 'What you learned' },
]

export function FlowNav({
  current,
  slug,
}: {
  current: Stage
  /** Omitted on Connect, where no project has been chosen yet. */
  slug?: string
}) {
  return (
    <nav className="flow" aria-label="Where you are">
      <ol>
        {STAGES.map((stage) => {
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
              <span className="flow-n">{stage.n}</span>
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
      </ol>
    </nav>
  )
}
