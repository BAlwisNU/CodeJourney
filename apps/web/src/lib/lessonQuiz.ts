import type { QuizQuestion } from './types'

/**
 * Which questions are asked while reading, and which are saved for the quiz.
 *
 * Shared because two pages have to agree exactly: the lesson hands the first
 * few out as checkpoints, one after each section, and the quiz page shows what
 * is left. If they disagreed a question would either be asked twice or never
 * asked at all.
 *
 * Positional, because lessons are written in the order they teach and the
 * questions in the order of the lesson, so question 2 is about section 2.
 *
 * One is always held back, so the quiz page can never be empty -- it is a stage
 * of the flow now, with its own tab, and arriving at a stage that has nothing
 * on it reads as a fault.
 */
export function splitQuestions(
  questions: QuizQuestion[],
  sectionCount: number
): { inline: QuizQuestion[]; rest: QuizQuestion[] } {
  const inlineCount = Math.min(sectionCount, Math.max(0, questions.length - 1))
  return {
    inline: questions.slice(0, inlineCount),
    rest: questions.slice(inlineCount),
  }
}
