import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { type IconName } from '../components/Icon'
import { type Lang } from '../components/LanguageCarousel'
import { ProjectBoard } from '../components/ProjectBoard'
import { TalkView } from '../components/TalkView'
import { TopicSequence } from '../components/TopicSequence'
import { PageFlick } from '../components/PageFlick'
import { api, token } from '../lib/api'
import { CURRICULUM, buildSequence } from '../lib/curriculum'
import type { Dashboard, DashboardBranch, ExerciseProgress, Project } from '../lib/types'

/**
 * The home. Three views behind one page, switched by the top-right page-flick:
 *
 *   home      -- the 3D language carousel + the focused language's topics
 *   projects  -- everything you've worked on, in progress first
 *   progress  -- what you've covered and what to do next
 *
 * Languages are the top level; topics (Lists, Loops, ...) sit under each one.
 * Only Python is live: C++, HTML and SQL are locked, because the execution
 * engine is Python-only (Pyodide in the browser, a Python sandbox on the
 * server). A real C++/HTML/SQL lesson needs its own executor, so those tiles
 * are honestly marked "coming soon" rather than linking to nothing.
 *
 * A deliberate absence, and it is load-bearing: the "progress" view shows
 * completion and topics, but NOT time-on-task or hint depth. Those are Week 7
 * dependent variables, and showing a participant their own values changes the
 * behaviour being measured. Same rule as GET /progress.
 */

// Topics, in teaching order. A Python exercise's `concept` is its topic.
const TOPICS: { key: string; label: string }[] = [
  { key: 'lists', label: 'Lists' },
  { key: 'loops', label: 'Loops' },
  { key: 'dicts', label: 'Dictionaries' },
  { key: 'strings', label: 'Strings' },
  { key: 'functions', label: 'Functions' },
  { key: 'file_io', label: 'Files' },
]
const TOPIC_LABEL = Object.fromEntries(TOPICS.map((t) => [t.key, t.label]))

// The languages, in carousel order. `locked` languages have no content and no
// executor yet; when one lands, drop `locked` and tag its exercises.
type LangMeta = {
  key: string
  short: string
  name: string
  blurb: string
  locked: boolean
}
const LANGUAGES: LangMeta[] = [
  { key: 'python', short: 'Py', name: 'Python', blurb: 'Where everyone should start. Runs in your browser.', locked: false },
  { key: 'cpp', short: 'C++', name: 'C++', blurb: 'Speed and control, closer to the machine.', locked: true },
  { key: 'html', short: '</>', name: 'HTML & CSS', blurb: 'Build things you can see, in the browser.', locked: true },
  { key: 'sql', short: 'SQL', name: 'SQL', blurb: 'Ask questions of data and get answers.', locked: true },
]

/* Home is the summary; Projects and Lessons are the two things it summarises.
   "Projects" used to mean the work log -- everything you had opened -- which
   is a different thing from the projects you are building and could not keep
   the name once those existed. That list is lessons, so it lives with them. */
const VIEWS = [
  { key: 'home', label: 'Home', icon: 'home' as IconName },
  { key: 'projects', label: 'Projects', icon: 'projects' as IconName },
  { key: 'lessons', label: 'Lessons', icon: 'reorder' as IconName },
  { key: 'talk', label: 'Ask for help', icon: 'journal' as IconName },
  { key: 'progress', label: 'Progress & goals', icon: 'progress' as IconName },
]

function statusHref(ex: ExerciseProgress): string {
  return ex.status === 'in_progress'
    ? `/exercise/${ex.slug}`
    : `/exercise/${ex.slug}/plan`
}

export function HomePage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const view = params.get('view') ?? 'home'

  const [data, setData] = useState<Dashboard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [focused, setFocused] = useState(0)

  useEffect(() => {
    api
      .progress()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  const langs: Lang[] = useMemo(() => {
    if (!data) return []
    return LANGUAGES.map((meta) => {
      // Everything currently in the platform is Python; locked languages have
      // nothing until their executor exists.
      const exercises = meta.key === 'python' ? data.exercises : []
      return {
        ...meta,
        exercises,
        solved: exercises.filter((e) => e.status === 'solved').length,
        total: exercises.length,
      }
    })
  }, [data])

  // parent lesson slug -> the practice branches the student built off it.
  const branchesBySlug = useMemo(() => {
    const map = new Map<string, DashboardBranch[]>()
    for (const b of data?.branches ?? []) {
      const arr = map.get(b.parent_slug) ?? []
      arr.push(b)
      map.set(b.parent_slug, arr)
    }
    return map
  }, [data])

  function setView(key: string) {
    setParams(key === 'home' ? {} : { view: key }, { replace: false })
  }
  function logOut() {
    token.clear()
    navigate('/')
  }

  if (error) return <p className="panel panel-error">{error}</p>
  if (!data) return <p className="muted home-loading">Loading…</p>

  const nothingYet = data.total_attempts === 0
  const focusedLang = langs[focused]

  // What the resume card offers. The API already nominates one via
  // continue_slug; falling back to the first unsolved exercise means a brand
  // new account still gets a single obvious place to start rather than a wall
  // of equal choices.
  const target =
    data.exercises.find((e) => e.slug === data.continue_slug) ??
    data.exercises.find((e) => e.status !== 'solved')
  const resume = target
    ? {
        slug: target.slug,
        title: target.title,
        concept: target.concept,
        solved: data.solved,
        total: data.total_exercises,
      }
    : null

  return (
    <div className="home">
      <header className="home-bar">
        <span className="wordmark">
          <span className="mark" aria-hidden>
            {'{ }'}
          </span>
          CodeJourney
        </span>
        <PageFlick views={VIEWS} active={view} onChange={setView} onLogout={logOut} />
      </header>

      <div className="home-view" key={view}>
        {view === 'home' && (
          <HomeView
            name={data.display_name}
            nothingYet={nothingYet}
            resume={resume}
            data={data}
            onGoto={setView}
          />
        )}
        {view === 'projects' && <ProjectsView />}
        {view === 'lessons' && (
          <LessonsView
            data={data}
            langs={langs}
            focused={focused}
            setFocused={setFocused}
            focusedLang={focusedLang}
            branchesBySlug={branchesBySlug}
          />
        )}
        {view === 'talk' && <TalkView data={data} />}
        {view === 'progress' && <ProgressView data={data} />}
      </div>
    </div>
  )
}

// --- Home: carousel + focused language's topics ----------------------------

function HomeView({
  name,
  nothingYet,
  resume,
  data,
  onGoto,
}: {
  name: string
  nothingYet: boolean
  resume: {
    slug: string
    title: string
    concept: string
    solved: number
    total: number
  } | null
  data: Dashboard
  onGoto: (view: string) => void
}) {
  // Newest work first. `last_attempt_at` is set by submitting, so this is what
  // you were actually doing rather than everything you have ever opened.
  const recent = [...data.exercises]
    .filter((e) => e.last_attempt_at)
    .sort((a, b) => (b.last_attempt_at ?? '').localeCompare(a.last_attempt_at ?? ''))
    .slice(0, 4)

  // Practice the coach built for this learner off the back of something they
  // found hard. It is on nobody else's dashboard.
  const madeForYou = data.branches.filter((b) => b.status !== 'solved').slice(0, 4)

  return (
    <>
      <div className="home-hero">
        <h1>
          {nothingYet ? 'Welcome, ' : 'Welcome back, '}
          <span className="grad">{name}</span>
        </h1>
      </div>

      {resume && (
        <Link className="resume" to={`/exercise/${resume.slug}/plan`}>
          <span className="resume-eyebrow">
            {nothingYet ? 'Start here' : 'Pick up where you left off'}
          </span>
          <span className="resume-title">{resume.title}</span>
          <span className="resume-meta muted">
            {resume.solved} of {resume.total} done
            {resume.concept ? ` · ${resume.concept}` : ''}
          </span>
          <span className="resume-go">{nothingYet ? 'Start →' : 'Continue →'}</span>
        </Link>
      )}

      <ProjectBoard />

      {recent.length > 0 && (
        <section className="strip">
          <div className="strip-head">
            <h2>Recent lessons</h2>
            <button type="button" className="linkish" onClick={() => onGoto('lessons')}>
              All lessons →
            </button>
          </div>
          <div className="strip-grid">
            {recent.map((ex) => (
              <Link key={ex.id} to={statusHref(ex)} className="strip-card">
                <span className="strip-title">{ex.title}</span>
                <span className="strip-meta muted small">
                  {ex.status === 'solved'
                    ? 'solved'
                    : `${ex.attempts} ${ex.attempts === 1 ? 'try' : 'tries'} so far`}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {madeForYou.length > 0 && (
        <section className="strip">
          <div className="strip-head">
            <h2>Made for you</h2>
            <span className="muted small">
              Practice your coach wrote after watching you work
            </span>
          </div>
          <div className="strip-grid">
            {madeForYou.map((b) => (
              <Link key={b.slug} to={`/exercise/${b.slug}/plan`} className="strip-card is-made">
                <span className="strip-title">{b.title}</span>
                <span className="strip-meta muted small">
                  {b.status === 'in_progress' ? 'in progress' : 'built for you'}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </>
  )
}


// --- Projects: the things you are building ---------------------------------

function ProjectsView() {
  return (
    <div className="subview">
      <h1>Your project lessons</h1>
      <p className="muted">
        Each one is a real thing to make. The lessons under it are the parts you
        need first.
      </p>
      <ProjectBoard heading={null} />
    </div>
  )
}

// --- Lessons: the curriculum, and everything you have worked on ------------

function LessonsView({
  data,
  langs,
  focused,
  setFocused,
  focusedLang,
  branchesBySlug,
}: {
  data: Dashboard
  langs: Lang[]
  focused: number
  setFocused: (i: number) => void
  focusedLang?: Lang
  branchesBySlug: Map<string, DashboardBranch[]>
}) {
  const worked = [
    ...data.exercises.filter((e) => e.status === 'in_progress'),
    ...data.exercises.filter((e) => e.status === 'solved'),
  ]

  const statusBySlug = new Map<string, ExerciseProgress['status']>()
  for (const e of focusedLang?.exercises ?? []) statusBySlug.set(e.slug, e.status)

  return (
    <div className="subview">
      <h1>Lessons</h1>
      <p className="muted">
        Everything there is to learn, and everything you have worked on.
      </p>

      {langs.length > 1 && (
        <div className="lang-pills" role="tablist" aria-label="Language">
          {langs.map((l, i) => (
            <button
              key={l.key}
              role="tab"
              type="button"
              aria-selected={i === focused}
              disabled={l.locked}
              className={i === focused ? 'lang-pill is-on' : 'lang-pill'}
              onClick={() => setFocused(i)}
            >
              {l.name}
              {l.locked && <span className="lang-pill-soon">soon</span>}
            </button>
          ))}
        </div>
      )}

      {worked.length > 0 && (
        <section className="worklog">
          <h2>Your work</h2>
          <div className="project-grid">
            {worked.map((ex) => (
              <Link
                key={ex.id}
                to={`/exercise/${ex.slug}`}
                className={ex.status === 'solved' ? 'project-card done' : 'project-card wip'}
              >
                <span className="project-mark" aria-hidden>
                  {ex.status === 'solved' ? '✓' : '◐'}
                </span>
                <span className="project-title">{ex.title}</span>
                <span className="muted small">
                  {ex.status === 'solved'
                    ? 'solved'
                    : `${ex.attempts} ${ex.attempts === 1 ? 'try' : 'tries'} so far`}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {focusedLang && !focusedLang.locked && (
        <section className="topics" key={focusedLang.key}>
          {CURRICULUM.map((topic) => {
            const nodes = buildSequence(topic, (slug) => statusBySlug.get(slug))
            if (!nodes.length) return null
            return (
              <div className="dash-topic" key={topic.key}>
                <div className="dash-topic-head">
                  <h2>{topic.label}</h2>
                </div>
                <p className="dash-topic-intro muted small">{topic.intro}</p>
                <TopicSequence nodes={nodes} branchesBySlug={branchesBySlug} />
              </div>
            )
          })}
        </section>
      )}
    </div>
  )
}


// --- Progress & goals ------------------------------------------------------

function ProgressView({ data }: { data: Dashboard }) {
  const { solved, total_exercises: total } = data
  const pct = total ? Math.round((solved / total) * 100) : 0
  const nextUp = data.exercises.find((e) => e.slug === data.continue_slug)

  // The goals half of "Progress & goals", which used to be missing entirely --
  // the page was three views of the same completion count and the word "goals"
  // in the title. A goal here is a thing you decided to build, so it is the
  // projects, measured in pieces rather than percent.
  const [projects, setProjects] = useState<Project[] | null>(null)
  useEffect(() => {
    let cancelled = false
    api
      .projects()
      .then((r) => !cancelled && setProjects(r.projects))
      .catch(() => !cancelled && setProjects([]))
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="subview">
      <h1>Progress &amp; goals</h1>
      <p className="muted">
        How far you&rsquo;ve come, and a good next step. (We keep your times and
        hint use private — even from you — so they can&rsquo;t change how you
        work.)
      </p>

      <section className="panel">
        <div className="progress-head">
          <h2>Overall</h2>
          <span className="muted small">{solved} of {total} solved</span>
        </div>
        <div
          className="bar big"
          role="progressbar"
          aria-valuenow={solved}
          aria-valuemin={0}
          aria-valuemax={total}
        >
          <span style={{ width: `${pct}%` }} />
        </div>
      </section>

      {projects !== null && projects.length > 0 && (
        <section className="panel">
          <div className="progress-head">
            <h2>Your goals</h2>
            <span className="muted small">
              {projects.filter((p) => p.built).length} of {projects.length} built
            </span>
          </div>
          <ul className="goals">
            {projects.map((project) => {
              const done = project.total ? (project.done / project.total) * 100 : 0
              return (
                <li key={project.id} className={project.built ? 'goal is-built' : 'goal'}>
                  <div className="goal-top">
                    <span className="goal-name">{project.title}</span>
                    {project.built ? (
                      <span className="badge badge-quiet">built</span>
                    ) : (
                      <span className="muted small">
                        {project.done} of {project.total} pieces
                      </span>
                    )}
                  </div>
                  <div
                    className="bar bar-sm"
                    role="progressbar"
                    aria-valuenow={project.done}
                    aria-valuemin={0}
                    aria-valuemax={project.total}
                    aria-label={project.title}
                  >
                    <span style={{ width: `${done}%` }} />
                  </div>
                  {/* One link, and which one depends on where the project is:
                      the next piece while there are pieces left, the build
                      itself once there are not. */}
                  <Link
                    className="goal-go"
                    to={
                      project.next_slug
                        ? `/exercise/${project.next_slug}/plan`
                        : `/build/${project.id}`
                    }
                  >
                    {project.next_slug
                      ? project.done === 0
                        ? 'Start the first piece →'
                        : 'Carry on →'
                      : project.built
                        ? 'Open it →'
                        : 'Build it →'}
                  </Link>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {data.concepts.length > 0 && (
        <section className="panel">
          <h2>By topic</h2>
          <ul className="concepts">
            {data.concepts.map((c) => (
              <li key={c.concept}>
                <span className="concept-name">
                  {TOPIC_LABEL[c.concept] ?? c.concept}
                </span>
                <span className="muted small">{c.solved}/{c.total}</span>
                <div className="bar bar-sm">
                  <span style={{ width: `${c.total ? (c.solved / c.total) * 100 : 0}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {nextUp && (
        <section className="panel next-up">
          <div>
            <p className="eyebrow">Your next goal</p>
            <h2>{nextUp.title}</h2>
            <p className="muted small">{TOPIC_LABEL[nextUp.concept] ?? nextUp.concept}</p>
          </div>
          <Link className="btn btn-primary" to={statusHref(nextUp)}>
            {nextUp.status === 'in_progress' ? 'Carry on' : 'Start'}
          </Link>
        </section>
      )}
    </div>
  )
}
