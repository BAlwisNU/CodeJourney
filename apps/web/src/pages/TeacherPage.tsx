import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ClassesView } from '../components/teacher/ClassesView'
import { DifficultyView } from '../components/teacher/DifficultyView'
import { OverviewView } from '../components/teacher/OverviewView'
import { QuestionsView } from '../components/teacher/QuestionsView'
import { StudentPanel } from '../components/teacher/StudentPanel'
import { StudentsView } from '../components/teacher/StudentsView'
import { api, token } from '../lib/api'
import { forgetAccount } from '../lib/session'
import type { TeacherHome } from '../lib/types'

/**
 * The teaching app.
 *
 * A separate top-level page rather than a tab inside the student dashboard,
 * because a teacher and a student are not doing versions of the same thing.
 * A student's app is organised around what they are building; this one is
 * organised around four questions, in the order a teacher asks them:
 *
 *   Today       who needs me right now?
 *   Students    how is each person doing?
 *   Difficulty  what should I reteach?
 *   Questions   what did they ask me?
 *   Classes     who is even in this?
 *
 * The shell owns exactly two things — which view is showing, and which class is
 * in scope — and hands the data down. Each view is its own file so that adding
 * a fifth question doesn't mean editing a thousand-line component.
 */

const VIEWS = ['today', 'students', 'difficulty', 'questions', 'classes'] as const
type View = (typeof VIEWS)[number]

const LABELS: Record<View, string> = {
  today: 'Today',
  students: 'Students',
  difficulty: 'Difficulty',
  questions: 'Questions',
  classes: 'Classes',
}

export function TeacherPage() {
  const navigate = useNavigate()
  const [view, setView] = useState<View>('today')
  const [classroomId, setClassroomId] = useState<string | undefined>(undefined)
  const [data, setData] = useState<TeacherHome | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [openStudent, setOpenStudent] = useState<string | null>(null)

  const load = useCallback(() => {
    api
      .teacherHome(classroomId)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [classroomId])

  /**
   * After making a class, land on the class list.
   *
   * Making the first one flips the whole page out of its setup state and into
   * the tabs, which defaults to Today -- so without this the code the teacher
   * just created, and needs to read out in the next thirty seconds, disappears
   * behind a tab they have not been told about.
   */
  const afterClassChange = useCallback(() => {
    load()
    setView('classes')
  }, [load])

  useEffect(() => {
    load()
  }, [load])

  function signOut() {
    token.clear()
    forgetAccount()
    navigate('/')
  }

  if (error) return <p className="panel panel-error">{error}</p>
  if (!data) return <p className="muted">Loading…</p>

  // A brand-new teacher gets the setup card and nothing else. Five tabs of
  // empty tables read as broken rather than as new, and the only useful action
  // at that moment is making a class.
  const firstRun = !data.has_class

  return (
    <div className="teach">
      <header className="teach-bar">
        <div className="teach-brand">
          <span className="teach-mark" aria-hidden>
            {'{ }'}
          </span>
          <span>CodeJourney</span>
          <span className="teach-role">Teaching</span>
        </div>

        <div className="teach-bar-right">
          {data.classrooms.length > 1 && !firstRun && (
            <label className="teach-scope">
              <span className="sr-only">Class</span>
              <select
                value={classroomId ?? ''}
                onChange={(e) => setClassroomId(e.target.value || undefined)}
              >
                <option value="">All my classes</option>
                {data.classrooms.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <span className="teach-name">{data.display_name}</span>
          <Link className="linkish" to="/exercises">
            Student view
          </Link>
          <button type="button" className="linkish" onClick={signOut}>
            Log out
          </button>
        </div>
      </header>

      {firstRun ? (
        <main className="teach-main">
          <div className="teach-head">
            <h1>Welcome, {data.display_name.split(' ')[0]}</h1>
            <p className="muted">
              One thing to do first: make a class and give your students its
              code. Everything else fills itself in from there.
            </p>
          </div>
          <ClassesView classrooms={data.classrooms} onChanged={afterClassChange} />
        </main>
      ) : (
        <>
          <nav className="teach-tabs" role="tablist" aria-label="Teaching views">
            {VIEWS.map((key) => (
              <button
                key={key}
                role="tab"
                type="button"
                aria-selected={view === key}
                className={view === key ? 'teach-tab is-on' : 'teach-tab'}
                onClick={() => setView(key)}
              >
                {LABELS[key]}
                {key === 'questions' && data.open_questions > 0 && (
                  <span className="teach-pip">{data.open_questions}</span>
                )}
                {key === 'students' && data.needs_help > 0 && (
                  <span className="teach-pip is-flag">{data.needs_help}</span>
                )}
              </button>
            ))}
          </nav>

          <main className="teach-main">
            {view === 'today' && (
              <OverviewView
                data={data}
                onOpenStudent={setOpenStudent}
                onGoto={setView}
              />
            )}
            {view === 'students' && (
              <StudentsView data={data} onOpenStudent={setOpenStudent} />
            )}
            {view === 'difficulty' && <DifficultyView data={data} />}
            {view === 'questions' && <QuestionsView classroomId={classroomId} />}
            {view === 'classes' && (
              <ClassesView classrooms={data.classrooms} onChanged={afterClassChange} />
            )}
          </main>
        </>
      )}

      {openStudent && (
        <StudentPanel userId={openStudent} onClose={() => setOpenStudent(null)} />
      )}
    </div>
  )
}
