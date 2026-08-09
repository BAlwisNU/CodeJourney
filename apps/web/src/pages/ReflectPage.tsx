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

      {/* Back first and quiet, then the title. It used to be four loose
          elements in a stack -- eyebrow, title, paragraph, a raw underlined
          link last -- each at its own spacing, so the header read as a list of
          leftovers rather than as one thing. */}
      <header className="reflect-head">
        <Link className="reflect-back" to={`/exercise/${slug}`}>
          ← Back to the code
        </Link>
        <h1>{exercise.title}</h1>
        <p className="reflect-sub">
          Nothing here is marked. It is for you.
        </p>
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

      {/* Two sections, each announced. The conversation goes to a model; the
          journal never does (routers/reflections.py), and that difference is
          the most important thing on the page -- so each says who can read it
          rather than relying on a divider between them to imply it. */}
      <section className="reflect-part">
        <div className="reflect-part-head">
          <h2>Talk it through</h2>
          <span className="reflect-who">Your coach can read this</span>
        </div>
        <Tutor exerciseId={exercise.id} solved onLessonCreated={handleLessonCreated} />
      </section>

      <section className="reflect-part">
        <div className="reflect-part-head">
          <h2>Your journal</h2>
          <span className="reflect-who is-private">Nothing reads this but you</span>
        </div>
        <Journal exerciseId={exercise.id} />
      </section>
    </div>
  )
}
