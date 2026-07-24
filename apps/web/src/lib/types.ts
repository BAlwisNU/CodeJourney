/**
 * Shapes returned by packages/harness/harness.py.
 *
 * These mirror the harness's output exactly. They are hand-written rather than
 * generated because the harness is Python and the source of truth is that file,
 * not this one -- if they drift, the harness is right and this is wrong.
 */

export type HarnessError = {
  type: string
  message: string
  line: number | null
  traceback: string
}

export type TestResult = {
  name: string
  status: 'pass' | 'fail' | 'error'
  hidden: boolean
  /** null when hidden -- the server strips these before they reach us. */
  args: string | null
  expected: string | null
  actual: string | null
  stdout: string
  error: HarnessError | null
}

export type HarnessResult = {
  phase:
    | 'loaded'
    | 'syntax_error'
    | 'missing_entrypoint'
    | 'timeout'
    | 'harness_error'
  error: HarnessError | null
  stdout: string
  tests: TestResult[]
  passed: boolean
  summary: { passed: number; total: number }
}

export type Exercise = {
  id: string
  slug: string
  title: string
  theme: string
  concept: string
  variant: 'themed' | 'generic'
  prompt_md: string
  starter_code: string
  entrypoint: string
  tests: { name: string; hidden: boolean; args: string | null; expected: string | null }[]
}

export type ExerciseProgress = {
  id: string
  slug: string
  title: string
  concept: string
  theme: string
  variant: 'themed' | 'generic'
  status: 'solved' | 'in_progress' | 'not_started'
  attempts: number
  last_attempt_at: string | null
}

export type ConceptProgress = {
  concept: string
  solved: number
  total: number
}

/**
 * Note what the server deliberately doesn't send: time-on-task and hint depth.
 * Both are Week 7 dependent variables, and showing a participant their own
 * values changes the behaviour being measured. See apps/api/app/routers/progress.py.
 */
export type Dashboard = {
  display_name: string
  role: 'student' | 'instructor'
  solved: number
  total_exercises: number
  total_attempts: number
  concepts: ConceptProgress[]
  continue_slug: string | null
  exercises: ExerciseProgress[]
}

export type SubmitResponse = {
  submission_id: string
  passed: boolean
  test_results: HarnessResult
  translated_error: string | null
  hint_level: number
  hint: string | null
  attempt_number: number
}

export type Reflection = {
  id: string
  exercise_id: string | null
  what_i_tried: string
  where_i_got_stuck: string
  how_i_fixed_it: string
  created_at: string
  updated_at: string
}

export type Account = {
  id: string
  email: string
  display_name: string
  role: 'student' | 'instructor'
  consented_at: string | null
  consent_withdrawn_at: string | null
  created_at: string
}

export type Draft = {
  exercise_id: string
  code: string
  updated_at: string
}

// --- learning content (Plan stage) ---

export type QuizQuestion = { id: string; prompt: string; options: string[] }

export type Lesson = {
  id: string
  slug: string
  title: string
  concept: string
  body_md: string
  questions: QuizQuestion[]
  completed: boolean
}

export type QuizGrade = {
  correct: number
  total: number
  results: {
    question_id: string
    correct: boolean
    correct_index: number
    explanation: string
  }[]
}

export type Parsons = { id: string; prompt: string; shuffled_lines: string[] }

export type ParsonsCheck = {
  correct: boolean
  /** How many lines from the top are right — never which ones are wrong. */
  correct_prefix: number
  total_lines: number
}

// --- portfolio ---

export type PortfolioEntry = {
  exercise_id: string
  slug: string
  title: string
  theme: string
  concept: string
  solved_at: string | null
  attempts: number
  code: string | null
  reflection: Reflection | null
}

export type Portfolio = {
  display_name: string
  solved: number
  total_attempts: number
  concepts_touched: string[]
  entries: PortfolioEntry[]
}

// --- instructor ---

export type InstructorOverview = {
  students: {
    user_id: string
    display_name: string
    solved: number
    total_exercises: number
    attempts: number
    max_hint_level: number
    needs_help: boolean
  }[]
  common_errors: { error_type: string; count: number }[]
  total_students: number
  total_submissions: number
  divergence_incidents: number
}
