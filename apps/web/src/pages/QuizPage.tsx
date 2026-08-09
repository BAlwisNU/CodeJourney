import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { FlowNav } from '../components/FlowNav'
import { InlineMarkdown } from '../components/Markdown'
import { api } from '../lib/api'
import { parseBlocks, toSections } from '../lib/lessonBlocks'
import { splitQuestions } from '../lib/lessonQuiz'
import type { Exercise, Lesson, QuizGrade } from '../lib/types'

/**
 * Stage 3 — Quiz. The questions that were not asked while reading.
 *
 * Its own stage rather than a panel at the bottom of the lesson, so that
 * checking what stuck is a thing you go and do, and so the lesson page ends
 * with the lesson.
 *
 * Nothing here is a gate, exactly as on the lesson page. Every route onward is
 * open whatever you score, and the quiz can be skipped entirely -- a student who
 * already knows lists should not have to click through it to reach the editor,
 * and one who is struggling must not be locked out of the exercise by it.
 */
export function QuizPage() {
  const { slug = '' } = useParams()
  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [grade, setGrade] = useState<QuizGrade | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const ex = await api.exercise(slug)
      if (cancelled) return
      setExercise(ex)
      const l = await api.lesson(ex.concept).catch(() => null)
      if (cancelled) return
      setLesson(l)
    }
    load()
    return () => {
      cancelled = true
    }
  }, [slug])

  // Must match the lesson page's split exactly, or a question is asked twice
  // or never. See lib/lessonQuiz.
  const questions = useMemo(() => {
    if (!lesson) return []
    const sections = toSections(parseBlocks(lesson.body_md)).filter((s) => s.heading)
    return splitQuestions(lesson.questions, sections.length).rest
  }, [lesson])

  async function submit() {
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
      <FlowNav current="quiz" slug={slug} />

      <header className="plan-head">
        <h1>Quiz: {exercise.title}</h1>
        <Link className="plan-skip" to={`/exercise/${slug}`}>
          Skip to the editor →
        </Link>
      </header>

      {questions.length > 0 ? (
        <section className="panel">
          <h2>Check what stuck</h2>
          <p className="muted small">
            {questions.length === 1
              ? 'One question'
              : `${questions.length} questions`}
            , no marks, no time limit. Getting one wrong here is cheaper than
            getting it wrong in the editor.
          </p>

          <ol className="quiz">
            {questions.map((question) => {
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
                    <p className={outcome.correct ? 'quiz-why ok' : 'quiz-why'}>
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
              onClick={submit}
              disabled={busy || questions.some((q) => answers[q.id] === undefined)}
            >
              {busy ? 'Checking…' : 'Check my answers'}
            </button>
          ) : (
            <p className="muted">
              {grade.correct} of {grade.total} right.{' '}
              {grade.correct === grade.total
                ? 'Straight on to the editor.'
                : 'Have a read of the explanations, then carry on — this was never a test.'}
            </p>
          )}
        </section>
      ) : (
        <p className="panel muted">
          No quiz written for this concept yet — go straight to the editor.
        </p>
      )}

      <div className="plan-foot">
        {/* Back as well as forward. The quiz is where you find out you skimmed
            something, and the fix for that is the lesson, not the editor. */}
        <Link className="btn" to={`/exercise/${slug}/plan`}>
          ← Back to the lesson
        </Link>
        <Link className="btn btn-primary btn-lg" to={`/exercise/${slug}`}>
          {grade ? 'Now let me write it' : 'Skip ahead and write it'} →
        </Link>
      </div>
    </div>
  )
}
