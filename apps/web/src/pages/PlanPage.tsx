import { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, useParams } from 'react-router-dom'

import { FlowNav } from '../components/FlowNav'
import { Checkpoint } from '../components/lesson/Checkpoint'
import { LessonBody } from '../components/lesson/LessonBody'
import { LessonVideo } from '../components/lesson/LessonVideo'
import { ListLab } from '../components/lesson/ListLab'
import { Parsons } from '../components/Parsons'
import { api } from '../lib/api'
import { splitQuestions } from '../lib/lessonQuiz'
import {
  firstListInLesson,
  parseBlocks,
  readingMinutes,
  toSections,
  videosIn,
} from '../lib/lessonBlocks'
import type { Exercise, Lesson, Parsons as ParsonsData } from '../lib/types'

/**
 * Stage 1 — Read & Watch, in three views.
 *
 *   read         the lesson, with a checkpoint question after each section
 *   watch        whatever videos the lesson declares
 *   interactive  the playable loop and the Parsons warm-up
 *
 * The stage was already three different kinds of thing stacked in one column,
 * and stacking them meant the interactive parts sat below a screenful of prose,
 * where only a reader who was already committed would ever reach them.
 * Splitting them makes each one somewhere you can go, and makes "watch" a real
 * option rather than a word in the tab's name.
 *
 * The view lives in the URL, so a tab is linkable and the back button does what
 * it should. An unknown or missing view falls back to reading.
 *
 * Nothing here is a gate. Every part can be skipped and the editor is always
 * one click away: a student who already knows lists shouldn't have to click
 * through any of this, and one who is struggling shouldn't be locked out of the
 * exercise by it.
 */

type View = 'read' | 'watch' | 'interactive'

const VIEWS: { key: View; label: string }[] = [
  { key: 'read', label: 'Read' },
  { key: 'watch', label: 'Watch' },
  { key: 'interactive', label: 'Interactive' },
]

export function PlanPage() {
  const { slug = '', view } = useParams()
  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [parsons, setParsons] = useState<ParsonsData | null>(null)

  const current: View = view === 'watch' || view === 'interactive' ? view : 'read'

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

  // Parsed once and shared. Several things below need the block list, and
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
  const videos = useMemo(() => videosIn(blocks), [blocks])

  if (!exercise) return <p className="muted">Loading…</p>

  // The lesson asks the first few as checkpoints; the quiz page shows the
  // rest. Both pages read the same function so a question cannot be asked
  // twice or dropped between them.
  const sectionCount = toSections(blocks).filter((s) => s.heading).length
  const { inline } = splitQuestions(lesson?.questions ?? [], sectionCount)

  const hasInteractive = Boolean(lab || parsons)

  /** A line under each tab, so it says what is behind it before you click. */
  const hintFor = (key: View) => {
    if (key === 'read') return lesson ? `${readingMinutes(blocks)} min` : 'nothing yet'
    if (key === 'watch') {
      if (!videos.length) return 'nothing yet'
      return videos.length === 1 ? '1 video' : `${videos.length} videos`
    }
    return hasInteractive ? 'try it yourself' : 'nothing yet'
  }

  return (
    <div className="plan">
      <FlowNav current="plan" slug={slug} />

      <header className="plan-head">
        <h1>Before you write: {exercise.title}</h1>
        <Link className="btn btn-primary" to={`/exercise/${slug}`}>
          Skip to the editor →
        </Link>
      </header>

      <nav className="views" aria-label="How to work through this lesson">
        {VIEWS.map((v) => (
          <NavLink
            key={v.key}
            // `read` is the bare /plan URL, so the tab a learner lands on by
            // default and the tab they click back to are the same address.
            to={
              v.key === 'read'
                ? `/exercise/${slug}/plan`
                : `/exercise/${slug}/plan/${v.key}`
            }
            className={v.key === current ? 'view on' : 'view'}
            aria-current={v.key === current ? 'page' : undefined}
          >
            <span className="view-text">
              <strong>{v.label}</strong>
              <span className="view-hint">{hintFor(v.key)}</span>
            </span>
          </NavLink>
        ))}
      </nav>

      {current === 'read' &&
        (lesson ? (
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
        ) : (
          <p className="panel muted">
            No lesson written for this concept yet — go straight to the editor.
          </p>
        ))}

      {current === 'watch' && (
        <section className="panel">
          <h2>Watch</h2>
          {videos.length > 0 ? (
            <>
              <p className="muted small">
                {videos.length === 1
                  ? 'One video for this lesson.'
                  : `${videos.length} videos for this lesson.`}{' '}
                Nothing here is required — the reading covers the same ground.
              </p>
              {videos.map((video, i) => (
                <LessonVideo key={i} url={video.url} title={video.title} />
              ))}
            </>
          ) : (
            /* An honest empty state. A tab that silently shows nothing reads as
               broken; one that says what it is for reads as unfinished, which
               is what it is. */
            <div className="views-empty">
              <p>
                <strong>No video for this lesson yet.</strong>
              </p>
              <p className="muted">
                The reading covers everything you need, and the interactive
                walkthrough shows the loop actually running.
              </p>
              <p className="views-empty-go">
                <Link className="btn" to={`/exercise/${slug}/plan`}>
                  Read it instead
                </Link>
                {hasInteractive && (
                  <Link className="btn" to={`/exercise/${slug}/plan/interactive`}>
                    Watch it run →
                  </Link>
                )}
              </p>
            </div>
          )}
        </section>
      )}

      {current === 'interactive' &&
        (hasInteractive ? (
          <>
            {lab && <ListLab items={lab.items} name={lab.name} />}
            {parsons && <Parsons data={parsons} />}
          </>
        ) : (
          <div className="panel views-empty">
            <p>
              <strong>Nothing interactive for this lesson yet.</strong>
            </p>
            <p className="muted">The reading is the whole lesson for now.</p>
            <p className="views-empty-go">
              <Link className="btn" to={`/exercise/${slug}/plan`}>
                Read it instead
              </Link>
            </p>
          </div>
        ))}

      <div className="plan-foot">
        <Link className="btn btn-primary btn-lg" to={`/exercise/${slug}/quiz`}>
          I&rsquo;m ready — take the quiz →
        </Link>
      </div>
    </div>
  )
}
