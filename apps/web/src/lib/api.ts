import type {
  Account,
  Dashboard,
  Draft,
  InstructorOverview,
  Lesson,
  Parsons,
  ParsonsCheck,
  Portfolio,
  QuizGrade,
  Exercise,
  HarnessResult,
  Reflection,
  SubmitResponse,
} from './types'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const TOKEN_KEY = 'codejourney.token'

export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (value: string) => localStorage.setItem(TOKEN_KEY, value),
  clear: () => localStorage.removeItem(TOKEN_KEY),
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

  me: () => request<Account>('/auth/me'),

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

  parsons: (slug: string) => request<Parsons | null>(`/learn/parsons/${slug}`),

  checkParsons: (problemId: string, ordering: string[]) =>
    request<ParsonsCheck>(`/learn/parsons/${problemId}/check`, {
      method: 'POST',
      body: JSON.stringify({ ordering }),
    }),

  portfolio: () => request<Portfolio>('/portfolio'),

  instructor: () => request<InstructorOverview>('/instructor'),

  health: () =>
    request<{ python_version: string; pyodide_version: string }>('/health'),
}
