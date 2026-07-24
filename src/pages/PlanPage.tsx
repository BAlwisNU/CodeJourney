import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { FlowNav } from '../components/FlowNav'
import { InlineMarkdown, Markdown } from '../components/Markdown'
import { Parsons } from '../components/Parsons'
import { api } from '../lib/api'
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
            <h2>{lesson.title}</h2>
            {/* The body's own leading heading would repeat the title above. */}
            <Markdown source={lesson.body_md.replace(/^##\s+.*\n/, '')} />
          </section>

          {lesson.questions.length > 0 && (
            <section className="panel">
              <h2>Quick check</h2>
              <p className="muted small">
                Four questions, no marks, no time limit. Getting one wrong here
                is cheaper than getting it wrong in the editor.
              </p>

              <ol className="quiz">
                {lesson.questions.map((question) => {
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
                          {outcome.explanation}
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
                    busy || Object.keys(answers).length < lesson.questions.length
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
