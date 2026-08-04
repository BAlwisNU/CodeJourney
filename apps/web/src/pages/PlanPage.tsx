import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { FlowNav } from '../components/FlowNav'
import { Checkpoint } from '../components/lesson/Checkpoint'
import { LessonBody } from '../components/lesson/LessonBody'
import { ListLab } from '../components/lesson/ListLab'
import { Parsons } from '../components/Parsons'
import { api } from '../lib/api'
import { splitQuestions } from '../lib/lessonQuiz'
import {
  firstListInLesson,
  parseBlocks,
  readingMinutes,
  toSections,
} from '../lib/lessonBlocks'
import type { Exercise, Lesson, Parsons as ParsonsData } from '../lib/types'

/**
 * Stage 2 — Read & Watch. The lesson, the playable loop, and the Parsons
 * warm-up. The quiz moved to its own stage; only the checkpoints asked while
 * reading are still here.
 *
 * Nothing here is a gate. Every part can be skipped, and "Go and write it" is
 * always available. This is scaffolding, not a checkpoint: a student who already
 * knows lists shouldn't have to click through a quiz to reach the editor, and
 * one who is struggling shouldn't be locked out of the exercise by a quiz score.
 */
export function PlanPage() {
  const { slug = '' } = useParams()
  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [parsons, setParsons] = useState<ParsonsData | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const ex = await api.exercise(slug)
      if (cancelled) return
      setExercise(ex)
      // Both are optional. Unwritten content degrades to "straight to the
      // editor" rather than an error page.
      const [l, p] = await Promise.all([
        api.lesson(ex.concept).catch(() => null),
        api.parsons(slug).catch(() => null),
      ])
      if (cancelled) return
      setLesson(l)
      setParsons(p)
    }
    load()
    return () => {
      cancelled = true
    }
  }, [slug])

  // Parsed once and shared. Three things below need the block list, and
  // `lab` hands an array to a component that memoises on it -- rebuilding it
  // every render would defeat that. Above the early return, because hooks
  // cannot run after one.
  const blocks = useMemo(
    () => (lesson ? parseBlocks(lesson.body_md) : []),
    [lesson]
  )

  /**
   * The playable loop, when the lesson is one it makes sense for.
   *
   * Gated on the concept and on the lesson actually containing a list of
   * strings: it traces the filter loop specifically, and drawing it over a
   * lesson about file handles would be a toy rather than a demonstration.
   */
  const lab = useMemo(
    () => (lesson?.concept === 'lists' ? firstListInLesson(blocks) : null),
    [lesson?.concept, blocks]
  )

  if (!exercise) return <p className="muted">Loading…</p>

  // The lesson asks the first few as checkpoints; the quiz page shows the
  // rest. Both pages read the same function so a question cannot be asked
  // twice or dropped between them.
  const sectionCount = toSections(blocks).filter((s) => s.heading).length
  const { inline } = splitQuestions(lesson?.questions ?? [], sectionCount)

  return (
    <div className="plan">
      <FlowNav current="plan" slug={slug} />

      <header className="plan-head">
        <h1>Before you write: {exercise.title}</h1>
        <Link className="btn btn-primary" to={`/exercise/${slug}`}>
          Skip to the editor →
        </Link>
      </header>

      {lesson ? (
        <>
          <section className="panel lesson">
            <div className="lesson-top">
              <h2>{lesson.title}</h2>
              <span className="lesson-time muted small">
                {readingMinutes(blocks)} min read
              </span>
            </div>
            {/* LessonBody strips the body's own leading heading itself -- it
                would repeat the title beside it. */}
            <LessonBody
              source={lesson.body_md}
              checkpointFor={(n) =>
                inline[n - 1] ? (
                  <Checkpoint lessonId={lesson.id} question={inline[n - 1]} />
                ) : null
              }
            />
          </section>

          {lab && <ListLab items={lab.items} name={lab.name} />}
        </>
      ) : (
        <p className="panel muted">
          No lesson written for this concept yet — go straight to the editor.
        </p>
      )}

      {parsons && <Parsons data={parsons} />}

      <div className="plan-foot">
        <Link className="btn btn-primary btn-lg" to={`/exercise/${slug}/quiz`}>
          I&rsquo;m ready — take the quiz →
        </Link>
      </div>
    </div>
  )
}
