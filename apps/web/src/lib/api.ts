import type {
  Project,
  Account,
  AskState,
  BranchLink,
  Classroom,
  HelpRequest,
  MyClass,
  TeacherHome,
  TeacherStudentDetail,
  Dashboard,
  Draft,
  GeneratedLesson,
  InstructorOverview,
  LearnerProfile,
  LearnerProfileInput,
  Lesson,
  LessonProposal,
  OnboardingPlan,
  Parsons,
  ParsonsCheck,
  Portfolio,
  QuizGrade,
  Exercise,
  HarnessResult,
  HintResponse,
  Reflection,
  TutorChatResponse,
  WelcomeState,
  TutorMessage,
  SubmitResponse,
} from './types'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * The API's origin, for the one case that can't go through `request` below:
 * "Continue with Google" is a full-page navigation to the API, not a fetch,
 * because the browser has to follow redirects to the provider and back.
 */
export const API_BASE = BASE

const TOKEN_KEY = 'codejourney.token'
/**
 * Which demo button (if any) produced the current token. Written by the landing
 * page, read synchronously so it can decide what to show without waiting on the
 * server -- see lib/demo.ts.
 */
export const DEMO_KIND_KEY = 'codejourney.demo'

export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (value: string) => {
    // Clearing the demo marker here, rather than at each call site, is what
    // makes it safe: every route that signs somebody in goes through this
    // function, so a real login can never inherit a stale "this is a demo"
    // flag from an earlier visit. The demo path re-sets it immediately after.
    localStorage.removeItem(DEMO_KIND_KEY)
    localStorage.setItem(TOKEN_KEY, value)
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(DEMO_KIND_KEY)
  },
}

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

// Login and register are the two places a 401 is a real answer ("wrong
// password") rather than a dead session, so they must not trigger the redirect
// below -- doing so would bounce the user away from the error they need to read.
const CREDENTIAL_PATHS = ['/auth/login', '/auth/register']

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  const auth = token.get()
  if (auth) headers.set('Authorization', `Bearer ${auth}`)

  const response = await fetch(`${BASE}${path}`, { ...init, headers })

  if (!response.ok) {
    // A 401 on any authenticated call means the token is dead -- expired (they
    // last 12 hours), or issued for a user that no longer exists, which happens
    // whenever the database is reseeded in development.
    //
    // Without this, RequireAuth sees a token in localStorage, renders the page,
    // and the user is stranded on a raw error string with no log-out button and
    // no way back. That is a participant in Week 7 losing their session and
    // quietly dropping out of the study, so it is worth handling globally rather
    // than page by page.
    if (response.status === 401 && !CREDENTIAL_PATHS.includes(path)) {
      token.clear()
      // Full navigation rather than a router push: this module has no router
      // context, and a hard load also clears any stale in-memory state.
      if (window.location.pathname !== '/login') {
        window.location.assign('/login?expired=1')
      }
      throw new ApiError('Your session has expired. Please log in again.', 401)
    }

    const body = await response.json().catch(() => ({}))
    throw new ApiError(
      body.detail ?? `Request failed (${response.status})`,
      response.status
    )
  }

  // A 204 has no body, and calling .json() on one throws "Unexpected end of
  // JSON input" -- which surfaces as a thrown error from a call that actually
  // succeeded. Every endpoint that returns no content hit this.
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined as T
  }
  return response.json() as Promise<T>
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (
    email: string,
    password: string,
    display_name: string,
    consent_to_research = false
  ) =>
    request<{ access_token: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name, consent_to_research }),
    }),

  /**
   * Which third-party sign-in buttons to show. Driven by the server rather
   * than hard-coded, so a deployment with no Microsoft credentials shows one
   * button instead of a second that leads nowhere.
   */
  oauthProviders: () =>
    request<{
      providers: { key: string; label: string; configured: boolean }[]
    }>('/auth/oauth/providers'),

  /**
   * Mint a throwaway account for the landing page's demo buttons. A fresh one
   * per click, so two visitors never share -- or undo -- each other's work.
   */
  startDemo: (with_progress: boolean) =>
    request<{ access_token: string }>('/auth/demo', {
      method: 'POST',
      body: JSON.stringify({ with_progress }),
    }),

  me: () => request<Account>('/auth/me'),

  /**
   * The learner's own goals and project ideas. Note what isn't here: the
   * experience answer from the welcome step. The API has no schema capable of
   * returning it, so there is nothing for this client to ask for.
   */
  learnerProfile: () => request<LearnerProfile>('/auth/me/profile'),

  /**
   * Save part or all of the welcome step. Fields left out are left alone --
   * which is what lets the account page edit goals without clearing the
   * experience answer it isn't allowed to read.
   */
  saveLearnerProfile: (body: Partial<LearnerProfileInput>) =>
    request<LearnerProfile>('/auth/me/profile', {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  // --- the welcome chat, step three of signing up ---

  /** Everything the chat page needs: availability, greeting, history, plan. */
  welcomeState: () => request<WelcomeState>('/onboarding/welcome'),

  welcomeChat: (message: string) =>
    request<{ reply: string; plan: OnboardingPlan }>('/onboarding/welcome/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),

  /** The plan on its own, for the account page. */
  onboardingPlan: () => request<OnboardingPlan>('/onboarding/plan'),

  /** Grant or withdraw study consent. Withdrawal must be as easy as granting. */
  setConsent: (consent_to_research: boolean) =>
    request<Account>('/auth/me/consent', {
      method: 'PATCH',
      body: JSON.stringify({ consent_to_research }),
    }),

  exercises: () => request<Exercise[]>('/exercises'),

  /** The dashboard rollup. Computed server-side so the Week 5 mobile
   *  companion doesn't have to reimplement it. */
  progress: () => request<Dashboard>('/progress'),

  exercise: (slug: string) => request<Exercise>(`/exercises/${slug}`),

  /** Pull the next hint on demand, in addition to the ones that appear
   *  automatically after a failed submit. Climbs one rung per press, up to L4. */
  requestHint: (slug: string, session_id: string) =>
    request<HintResponse>(`/exercises/${slug}/hint`, {
      method: 'POST',
      body: JSON.stringify({ session_id }),
    }),

  /** The full worked answer, produced on demand and verified against the real
   *  tests before it's returned. The student chooses to step past the ladder. */
  showAnswer: (slug: string) =>
    request<{ solution: string }>(`/exercises/${slug}/solution`),

  /** Opens the sitting. Must be called when the editor mounts -- this is what
   *  starts the time-on-task clock, which is a dependent variable. */
  startSession: (slug: string) =>
    request<{ session_id: string; started_at: string }>(
      `/exercises/${slug}/session`,
      { method: 'POST' }
    ),

  submit: (payload: {
    exercise_id: string
    session_id: string
    code: string
    run_mode: 'run' | 'submit'
    client_results?: HarnessResult | null
  }) =>
    request<SubmitResponse>('/submissions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /** Work in progress. Server-side so it follows you between devices. */
  getDraft: (slug: string) => request<Draft | null>(`/exercises/${slug}/draft`),

  saveDraft: (slug: string, code: string) =>
    request<Draft>(`/exercises/${slug}/draft`, {
      method: 'PUT',
      body: JSON.stringify({ code }),
    }),

  resetDraft: async (slug: string) => {
    await fetch(`${BASE}/exercises/${slug}/draft`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token.get()}` },
    })
  },

  reflections: (exercise_id?: string) =>
    request<Reflection[]>(
      exercise_id ? `/reflections?exercise_id=${exercise_id}` : '/reflections'
    ),

  saveReflection: (body: {
    exercise_id: string
    what_i_tried: string
    where_i_got_stuck: string
    how_i_fixed_it: string
  }) =>
    request<Reflection>('/reflections', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // --- Plan stage ---

  lesson: (concept: string) => request<Lesson | null>(`/learn/lessons/${concept}`),

  gradeQuiz: (lessonId: string, answers: { question_id: string; chosen_index: number }[]) =>
    request<QuizGrade>(`/learn/lessons/${lessonId}/quiz`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    }),

  // --- projects ---

  projects: () => request<{ projects: Project[] }>('/projects'),

  addProject: (body: { title: string; blurb: string; topics: string[] }) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(body) }),

  setProjectBuilt: (id: string, built: boolean) =>
    request<Project>(`/projects/${id}/built`, {
      method: 'PATCH',
      body: JSON.stringify({ built }),
    }),

  setLessonKnown: (slug: string, known: boolean) =>
    request<void>(`/projects/lessons/${slug}/known`, {
      method: 'PUT',
      body: JSON.stringify({ known }),
    }),

  /** Which of my projects need this lesson. Used to say why it is being taught. */
  projectsForLesson: (slug: string) =>
    request<{ projects: Project[] }>(`/projects/for-lesson/${slug}`),

  parsons: (slug: string) => request<Parsons | null>(`/learn/parsons/${slug}`),

  checkParsons: (problemId: string, ordering: string[]) =>
    request<ParsonsCheck>(`/learn/parsons/${problemId}/check`, {
      method: 'POST',
      body: JSON.stringify({ ordering }),
    }),

  // --- Reflect stage: the AI tutor (distinct from the private journal) ---

  /** The saved conversation for a lesson, oldest first, so the chat comes back
   *  exactly as it was left. */
  tutorHistory: (exercise_id: string) =>
    request<TutorMessage[]>(`/tutor/history?exercise_id=${exercise_id}`),

  /** Send one new user turn. The prior conversation is the server's -- it's
   *  persisted per (user, lesson) and reloaded each turn. */
  tutorChat: (exercise_id: string, message: string) =>
    request<TutorChatResponse>('/tutor/chat', {
      method: 'POST',
      body: JSON.stringify({ exercise_id, message }),
    }),

  /** Accept the tutor's offer to build practice. The new exercise becomes a
   *  branch off `parentExerciseId` -- the lesson the chat is on. The server
   *  verifies it's solvable before returning a slug. */
  generateLesson: (proposal: LessonProposal, parentExerciseId: string) =>
    request<GeneratedLesson>('/tutor/lesson', {
      method: 'POST',
      body: JSON.stringify({
        concept: proposal.concept,
        focus: proposal.focus,
        title: proposal.title,
        parent_exercise_id: parentExerciseId,
      }),
    }),

  /** The AI-built branches the student made off this lesson, for links on the
   *  lesson's own page. */
  branches: (slug: string) =>
    request<BranchLink[]>(`/exercises/${slug}/branches`),

  portfolio: () => request<Portfolio>('/portfolio'),

  instructor: () => request<InstructorOverview>('/instructor'),

  // --- teaching ------------------------------------------------------------
  //
  // Grouped rather than scattered, and named for what a teacher would call
  // them. `teacherHome` is one request on purpose: five would mean five
  // spinners resolving in an order nobody chose.

  /** Whether this deployment offers teacher accounts. Says only yes or no —
   *  a server with it switched off shouldn't advertise that it exists. */
  teacherSignupAvailable: () =>
    request<{ enabled: boolean }>('/auth/register/teacher/available'),

  registerTeacher: (
    email: string,
    password: string,
    display_name: string,
    teacher_code: string
  ) =>
    request<{ access_token: string }>('/auth/register/teacher', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name, teacher_code }),
    }),

  /** The whole dashboard. Pass a classroom id to narrow to one class. */
  teacherHome: (classroomId?: string) =>
    request<TeacherHome>(
      classroomId ? `/teacher?classroom_id=${classroomId}` : '/teacher'
    ),

  teacherStudent: (userId: string) =>
    request<TeacherStudentDetail>(`/teacher/students/${userId}`),

  teacherStudentReflections: (userId: string) =>
    request<Reflection[]>(`/teacher/students/${userId}/reflections`),

  /** `join_code` is optional — left blank, the server draws one. */
  createClass: (name: string, join_code = '') =>
    request<Classroom>('/teacher/classes', {
      method: 'POST',
      body: JSON.stringify({ name, join_code }),
    }),

  setClassCode: (classroomId: string, join_code: string) =>
    request<Classroom>(`/teacher/classes/${classroomId}/code`, {
      method: 'PATCH',
      body: JSON.stringify({ join_code }),
    }),

  /** Throw away a project's written course so it can be built again. */
  deleteCourse: (projectId: string) =>
    request<void>(`/projects/${projectId}/course`, { method: 'DELETE' }),

  removeStudent: (classroomId: string, userId: string) =>
    request<void>(`/teacher/classes/${classroomId}/students/${userId}`, {
      method: 'DELETE',
    }),

  /** The teacher's queue, oldest first — newest-first buries whoever has been
   *  waiting longest. */
  helpInbox: (classroomId?: string) =>
    request<HelpRequest[]>(
      classroomId ? `/help/inbox?classroom_id=${classroomId}` : '/help/inbox'
    ),

  answerHelp: (id: string, answer: string) =>
    request<HelpRequest>(`/help/${id}/answer`, {
      method: 'POST',
      body: JSON.stringify({ answer }),
    }),

  // --- the student's side of all this --------------------------------------

  myClasses: () => request<MyClass[]>('/classes/mine'),

  joinClass: (code: string) =>
    request<MyClass>('/classes/join', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),

  leaveClass: (id: string) =>
    request<void>(`/classes/${id}`, { method: 'DELETE' }),

  myQuestions: () => request<AskState>('/help/mine'),

  askTeacher: (body: string, exercise_slug?: string) =>
    request<HelpRequest>('/help', {
      method: 'POST',
      body: JSON.stringify({ body, exercise_slug: exercise_slug ?? null }),
    }),

  closeQuestion: (id: string) =>
    request<HelpRequest>(`/help/${id}/close`, { method: 'POST' }),

  health: () =>
    request<{ python_version: string; pyodide_version: string }>('/health'),
}
