import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { FlowNav } from '../components/FlowNav'
import { Checkpoint } from '../components/lesson/Checkpoint'
import { LessonBody } from '../components/lesson/LessonBody'
import { InlineMarkdown } from '../components/Markdown'
import { Parsons } from '../components/Parsons'
import { api } from '../lib/api'
import { parseBlocks, readingMinutes, toSections } from '../lib/lessonBlocks'
import type { Exercise, Lesson, Parsons as ParsonsData, QuizGrade } from '../lib/types'

/**
 * Stage 2 — Plan. Lesson, quiz, and the Parsons warm-up.
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
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [grade, setGrade] = useState<QuizGrade | null>(null)
  const [busy, setBusy] = useState(false)

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

  async function submitQuiz() {
    if (!lesson) return
    setBusy(true)
    try {
      setGrade(
        await api.gradeQuiz(
          lesson.id,
          Object.entries(answers).map(([question_id, chosen_index]) => ({
            question_id,
            chosen_index,
          }))
        )
      )
    } finally {
      setBusy(false)
    }
  }

  if (!exercise) return <p className="muted">Loading…</p>

  const resultFor = (questionId: string) =>
    grade?.results.find((r) => r.question_id === questionId)

  /**
   * How many questions to ask inline, one per section, as you read.
   *
   * Positional: lessons are written in the order they teach, and the questions
   * are written in the order of the lesson, so question 2 is about section 2.
   * That holds across the curriculum because both come from the same author in
   * the same pass -- and where it doesn't, an inline question is still a
   * question about the lesson, which is the worst case.
   *
   * At least one is always kept back for the quiz at the end, so the page never
   * loses its recap, and a lesson with no sub-headings simply gets none.
   */
  const sectionCount = lesson
    ? toSections(parseBlocks(lesson.body_md)).filter((s) => s.heading).length
    : 0
  const questions = lesson?.questions ?? []
  const inlineCount = Math.min(sectionCount, Math.max(0, questions.length - 1))
  const inline = questions.slice(0, inlineCount)
  const remaining = questions.slice(inlineCount)

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
                {readingMinutes(parseBlocks(lesson.body_md))} min read
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

          {remaining.length > 0 && (
            <section className="panel">
              <h2>{inline.length > 0 ? 'Before you go' : 'Quick check'}</h2>
              <p className="muted small">
                {remaining.length === 1
                  ? 'One last question'
                  : `${remaining.length} questions`}
                , no marks, no time limit. Getting one wrong here is cheaper
                than getting it wrong in the editor.
              </p>

              <ol className="quiz">
                {remaining.map((question) => {
                  const outcome = resultFor(question.id)
                  return (
                    <li key={question.id} className="quiz-q">
                      <p className="quiz-prompt">
                        <InlineMarkdown source={question.prompt} />
                      </p>
                      <ul className="quiz-options">
                        {question.options.map((option, index) => {
                          const chosen = answers[question.id] === index
                          const isAnswer = outcome?.correct_index === index
                          return (
                            <li key={index}>
                              <label
                                className={
                                  outcome
                                    ? isAnswer
                                      ? 'opt opt-answer'
                                      : chosen
                                        ? 'opt opt-wrong'
                                        : 'opt'
                                    : chosen
                                      ? 'opt opt-chosen'
                                      : 'opt'
                                }
                              >
                                <input
                                  type="radio"
                                  name={question.id}
                                  checked={chosen}
                                  disabled={Boolean(grade)}
                                  onChange={() =>
                                    setAnswers({ ...answers, [question.id]: index })
                                  }
                                />
                                <InlineMarkdown source={option} />
                              </label>
                            </li>
                          )
                        })}
                      </ul>
                      {/* Explanation shows for right answers too -- someone who
                          guessed correctly has learned nothing yet. */}
                      {outcome && (
                        <p
                          className={
                            outcome.correct ? 'quiz-why ok' : 'quiz-why'
                          }
                        >
                          {outcome.correct ? '✓ ' : '✗ '}
                          <InlineMarkdown source={outcome.explanation} />
                        </p>
                      )}
                    </li>
                  )
                })}
              </ol>

              {!grade ? (
                <button
                  className="primary"
                  onClick={submitQuiz}
                  disabled={
                    busy ||
                    remaining.some((q) => answers[q.id] === undefined)
                  }
                >
                  {busy ? 'Checking…' : 'Check my answers'}
                </button>
              ) : (
                <p className="muted">
                  {grade.correct} of {grade.total} right.{' '}
                  {grade.correct === grade.total
                    ? 'Straight on to the warm-up.'
                    : 'Have a read of the explanations, then carry on — this was never a test.'}
                </p>
              )}
            </section>
          )}
        </>
      ) : (
        <p className="panel muted">
          No lesson written for this concept yet — go straight to the editor.
        </p>
      )}

      {parsons && <Parsons data={parsons} />}

      <div className="plan-foot">
        <Link className="btn btn-primary btn-lg" to={`/exercise/${slug}`}>
          I&rsquo;m ready — let me write it
        </Link>
      </div>
    </div>
  )
}
