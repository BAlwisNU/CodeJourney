import { useState } from 'react'

import { InlineMarkdown } from '../Markdown'
import { api } from '../../lib/api'
import type { QuizGrade, QuizQuestion } from '../../lib/types'

/**
 * One question, asked at the end of the section that teaches it.
 *
 * Four questions saved for the bottom of the page get answered from memory of
 * the whole lesson, which is the wrong thing to test and the wrong moment to
 * find out. Asked here, a wrong answer costs one section of re-reading and the
 * section is still on screen.
 *
 * It grades on the click rather than behind a submit button. There is one
 * answer to give, so a button would only add a step, and the explanation is
 * the point of asking at all.
 */
export function Checkpoint({
  lessonId,
  question,
}: {
  lessonId: string
  question: QuizQuestion
}) {
  const [chosen, setChosen] = useState<number | null>(null)
  const [grade, setGrade] = useState<QuizGrade['results'][number] | null>(null)
  const [busy, setBusy] = useState(false)

  async function choose(index: number) {
    if (grade || busy) return
    setChosen(index)
    setBusy(true)
    try {
      const result = await api.gradeQuiz(lessonId, [
        { question_id: question.id, chosen_index: index },
      ])
      setGrade(result.results[0] ?? null)
    } catch {
      // The lesson is readable without this. Leaving the choice shown and
      // ungraded is better than an error box in the middle of a paragraph.
      setChosen(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <aside
      className={
        grade ? (grade.correct ? 'ckpt ckpt-ok' : 'ckpt ckpt-no') : 'ckpt'
      }
    >
      <p className="ckpt-label">
        <span aria-hidden>✓</span> Quick check
      </p>
      <p className="ckpt-prompt">
        <InlineMarkdown source={question.prompt} />
      </p>

      <ul className="ckpt-options">
        {question.options.map((option, index) => {
          const isAnswer = grade?.correct_index === index
          const picked = chosen === index
          return (
            <li key={index}>
              <button
                type="button"
                disabled={Boolean(grade) || busy}
                onClick={() => choose(index)}
                className={
                  grade
                    ? isAnswer
                      ? 'ckpt-opt is-answer'
                      : picked
                        ? 'ckpt-opt is-wrong'
                        : 'ckpt-opt'
                    : picked
                      ? 'ckpt-opt is-picked'
                      : 'ckpt-opt'
                }
              >
                <span className="ckpt-mark" aria-hidden>
                  {grade && isAnswer ? '✓' : grade && picked ? '✗' : ''}
                </span>
                <InlineMarkdown source={option} />
              </button>
            </li>
          )
        })}
      </ul>

      {/* Shown for a right answer too: guessing correctly teaches nothing. */}
      {grade && (
        <p className="ckpt-why">
          <InlineMarkdown source={grade.explanation} />
        </p>
      )}
    </aside>
  )
}
