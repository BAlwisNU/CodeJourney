import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { AskTeacher } from '../components/AskTeacher'
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
/**
 * The two writing surfaces, and who reads each.
 *
 * `private` is not decoration: the journal is the one thing in the platform no
 * model ever sees, and the label saying so is the promise being kept in public.
 */
const REFLECT_TABS = [
  {
    key: 'teacher' as const,
    label: 'Ask your teacher',
    who: 'Your teacher can read this',
    private: false,
  },
  {
    key: 'journal' as const,
    label: 'Your journal',
    who: 'Nothing reads this but you',
    private: true,
  },
]

type Pane = (typeof REFLECT_TABS)[number]['key']

export function ReflectPage() {
  const { slug = '' } = useParams()
  // Opens on the journal: it is the step the lesson flow is actually asking
  // for, and asking a teacher is the thing you go and do when you need it.
  const [pane, setPane] = useState<Pane>('journal')
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

      {/* The two places you write for yourself, or for one person, sharing one
          panel. Three stacked sections meant the journal sat below a screenful
          of other things and was reached by whoever was already committed.

          The reader label moves with the tab and is never dropped. It is the
          most important thing on this page -- the whole promise is that the
          journal is not machine-read (routers/reflections.py) -- so "who sees
          this" has to be answerable before you type, not after you go looking
          for it. */}
      <section className="reflect-part">
        <nav className="rtabs" role="tablist" aria-label="Where to write">
          {REFLECT_TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              id={`rtab-${tab.key}`}
              aria-selected={pane === tab.key}
              aria-controls={`rpane-${tab.key}`}
              className={pane === tab.key ? 'rtab is-on' : 'rtab'}
              onClick={() => setPane(tab.key)}
            >
              <strong>{tab.label}</strong>
              <span className={tab.private ? 'rtab-who is-private' : 'rtab-who'}>
                {tab.who}
              </span>
            </button>
          ))}
        </nav>

        <div
          role="tabpanel"
          id={`rpane-${pane}`}
          aria-labelledby={`rtab-${pane}`}
        >
          {/* Both stay mounted. The journal autosaves a draft and the ask box
              holds a half-typed question; unmounting on a tab change would
              throw either away, which is the one thing a page about writing
              things down must never do. */}
          <div hidden={pane !== 'teacher'}>
            <AskTeacher exerciseSlug={slug} showHeading={false} />
          </div>
          <div hidden={pane !== 'journal'}>
            <Journal exerciseId={exercise.id} />
          </div>
        </div>
      </section>
    </div>
  )
}
