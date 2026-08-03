import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { FlowNav } from '../components/FlowNav'
import { Journal } from '../components/Journal'
import { Tutor } from '../components/Tutor'
import { api } from '../lib/api'
import type { BranchLink, Exercise, GeneratedLesson } from '../lib/types'

/**
 * The Reflect stage, on its own page.
 *
 * Create & Test is about the code; Reflect is about what you took from it, so
 * it gets its own room rather than living at the bottom of the editor. The AI
 * tutor and the private journal both live here. The tutor talks about the lesson
 * and your code; the journal never touches an LLM -- the same wall as everywhere
 * else (see apps/api/app/routers/reflections.py).
 *
 * Practice the tutor builds here is a branch off THIS lesson, so its links show
 * on arrival and update the moment a new one is made.
 */
export function ReflectPage() {
  const { slug = '' } = useParams()
  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [branches, setBranches] = useState<BranchLink[]>([])

  useEffect(() => {
    let cancelled = false
    api
      .exercise(slug)
      .then((data) => !cancelled && setExercise(data))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : String(err)))
    api
      .branches(slug)
      .then((b) => !cancelled && setBranches(b))
      .catch(() => {
        /* links are a bonus; never block reflection on them */
      })
    return () => {
      cancelled = true
    }
  }, [slug])

  function handleLessonCreated(lesson: GeneratedLesson) {
    setBranches((prev) =>
      prev.some((b) => b.slug === lesson.slug)
        ? prev
        : [...prev, { slug: lesson.slug, title: lesson.title, status: 'not_started' }]
    )
  }

  if (error && !exercise) return <p className="panel panel-error">{error}</p>
  if (!exercise) return <p className="muted">Loading…</p>

  return (
    <div className="exercise-page reflect-page">
      <FlowNav current="reflect" slug={slug} />

      <header className="reflect-head">
        <p className="eyebrow">Reflect</p>
        <h1>{exercise.title}</h1>
        <p className="muted">
          Talk it through and note what you learned. Nothing here changes your
          grade — it&rsquo;s just for you.
        </p>
        <Link className="link" to={`/exercise/${slug}`}>
          ← Back to the code
        </Link>
      </header>

      {branches.length > 0 && (
        <div className="branch-banner">
          <span className="muted small">Practice you built from this lesson:</span>
          {branches.map((b) => (
            <Link key={b.slug} to={`/exercise/${b.slug}`} className="branch-chip">
              {b.title}
              {b.status === 'solved' && (
                <span className="branch-done" aria-hidden>
                  {' '}
                  ✓
                </span>
              )}
            </Link>
          ))}
        </div>
      )}

      <Tutor exerciseId={exercise.id} solved onLessonCreated={handleLessonCreated} />
      <Journal exerciseId={exercise.id} />
    </div>
  )
}
