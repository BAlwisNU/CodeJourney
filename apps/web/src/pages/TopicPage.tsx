import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../lib/api'
import { TopicSequence } from '../components/TopicSequence'
import {
  buildSequence,
  CURRICULUM_BY_KEY,
  type Module,
} from '../lib/curriculum'
import type { Dashboard, ExerciseProgress } from '../lib/types'

/**
 * A topic's full learning path, foundations to applied.
 *
 * Modules render as a vertical roadmap grouped by level. A module's state comes
 * from whether its exercise is built and, if so, whether it's solved:
 *
 *   done      -- has an exercise, solved
 *   available -- has an exercise, not yet solved (links in)
 *   planned   -- no exercise yet; shown so the path ahead is visible
 *
 * Showing planned modules is the point of the page: a learner should see the
 * whole climb, not just the next step. Marking them plainly (rather than
 * linking to nothing) is the same honesty as the "coming soon" languages.
 */

type ModuleState = 'done' | 'available' | 'planned'

export function TopicPage() {
  const { topicKey = '' } = useParams()
  const topic = CURRICULUM_BY_KEY[topicKey]

  const [data, setData] = useState<Dashboard | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .progress()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  // slug -> the learner's status for that exercise.
  const statusBySlug = useMemo(() => {
    const map = new Map<string, ExerciseProgress>()
    data?.exercises.forEach((e) => map.set(e.slug, e))
    return map
  }, [data])

  if (!topic) {
    return (
      <main className="app">
        <p className="panel panel-error">That topic doesn’t exist yet.</p>
        <p>
          <Link className="link" to="/exercises">
            ← Back to home
          </Link>
        </p>
      </main>
    )
  }
  if (error) return <main className="app"><p className="panel panel-error">{error}</p></main>

  function stateOf(m: Module): ModuleState {
    if (!m.slug) return 'planned'
    const ex = statusBySlug.get(m.slug)
    return ex?.status === 'solved' ? 'done' : 'available'
  }

  const built = topic.modules.filter((m) => m.slug)
  const done = built.filter((m) => stateOf(m) === 'done').length
  const planned = topic.modules.length - built.length

  return (
    <main className="app topic-page">
      <p>
        <Link className="link" to="/exercises">
          ← Home
        </Link>
      </p>

      <header className="topic-header">
        <h1>{topic.label}</h1>
        <p className="muted">{topic.intro}</p>
        <p className="topic-stat">
          <strong>{done}</strong> done · <strong>{built.length}</strong> available
          now · <strong>{planned}</strong> more on the way
        </p>
      </header>

      <p className="muted small tree-hint">
        Left to right, basics to advanced. Follow a branch as far as you like.
      </p>

      <TopicSequence
        nodes={buildSequence(topic, (slug) => statusBySlug.get(slug)?.status)}
      />
    </main>
  )
}
