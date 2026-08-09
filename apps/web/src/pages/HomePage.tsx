import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { type IconName } from '../components/Icon'
import { type Lang } from '../components/LanguageCarousel'
import { TopicSequence } from '../components/TopicSequence'
import { PageFlick } from '../components/PageFlick'
import { api, token } from '../lib/api'
import { CURRICULUM, buildSequence } from '../lib/curriculum'
import type { Dashboard, DashboardBranch, ExerciseProgress } from '../lib/types'

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

const VIEWS = [
  { key: 'home', label: 'Home', icon: 'home' as IconName },
  { key: 'projects', label: 'Projects', icon: 'projects' as IconName },
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
            langs={langs}
            focused={focused}
            setFocused={setFocused}
            focusedLang={focusedLang}
            branchesBySlug={branchesBySlug}
          />
        )}
        {view === 'projects' && <ProjectsView data={data} />}
        {view === 'progress' && <ProgressView data={data} />}
      </div>
    </div>
  )
}

// --- Home: carousel + focused language's topics ----------------------------

function HomeView({
  name,
  nothingYet,
  langs,
  focused,
  setFocused,
  focusedLang,
  branchesBySlug,
  resume,
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
  langs: Lang[]
  focused: number
  setFocused: (i: number) => void
  focusedLang?: Lang
  branchesBySlug: Map<string, DashboardBranch[]>
}) {
  // slug -> the learner's status, for tagging each episode.
  const statusBySlug = useMemo(() => {
    const map = new Map<string, ExerciseProgress['status']>()
    for (const e of focusedLang?.exercises ?? []) map.set(e.slug, e.status)
    return map
  }, [focusedLang])

  return (
    <>
      <div className="home-hero">
        <h1>
          {nothingYet ? 'Welcome, ' : 'Welcome back, '}
          <span className="grad">{name}</span>
        </h1>
      </div>

      {/* The one thing this page is for.
          It used to be a small "Carry on" link inside the language carousel,
          three scrolls above six near-identical topic rows -- so the question
          the page exists to answer, "what do I do now?", was the hardest thing
          on it to find. */}
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
          <span className="resume-go">
            {nothingYet ? 'Start →' : 'Continue →'}
          </span>
        </Link>
      )}

      {/* Demoted to a row of pills. It was the largest thing on the page and
          three of its four options are marked "coming soon", so it spent the
          best space asking you to choose between one real answer and three
          disabled ones. */}
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

      {focusedLang && !focusedLang.locked && (
        <section className="topics" key={focusedLang.key}>
          <div className="lessons-head">
            <h2>{focusedLang.name} topics</h2>
            <span className="muted small">
              Left to right, basics to advanced — the whole path, laid out.
            </span>
          </div>

          {/* Every topic's tree, stacked. The learner sees the full map without
              a single click -- the dashboard IS the curriculum. */}
          {CURRICULUM.map((topic) => {
            const built = topic.modules.filter((m) => m.slug).length
            const doneCount = topic.modules.filter(
              (m) => m.slug && statusBySlug.get(m.slug) === 'solved'
            ).length
            const planned = topic.modules.length - built
            return (
              <div className="dash-topic" key={topic.key}>
                <div className="dash-topic-head">
                  <h3>{topic.label}</h3>
                  <span className="muted small">
                    {doneCount}/{built} done
                    {planned > 0 && ` · ${planned} more planned`}
                  </span>
                </div>
                <p className="dash-topic-intro muted small">{topic.intro}</p>
                <TopicSequence
                  nodes={buildSequence(topic, (slug) => statusBySlug.get(slug))}
                  branchesBySlug={branchesBySlug}
                />
              </div>
            )
          })}
        </section>
      )}

      {focusedLang?.locked && (
        <section className="topics coming-soon-panel">
          <h2>{focusedLang.name} is on the way</h2>
          <p className="muted">
            {focusedLang.name} needs its own way to run your code, separate from
            Python&rsquo;s. We&rsquo;re building it. For now, everything you learn
            in Python — loops, conditionals, functions, breaking things and
            fixing them — carries straight over when it lands.
          </p>
          <button className="primary" onClick={() => setFocused(0)}>
            Back to Python
          </button>
        </section>
      )}
    </>
  )
}

// --- Projects --------------------------------------------------------------

function ProjectsView({ data }: { data: Dashboard }) {
  const inProgress = data.exercises.filter((e) => e.status === 'in_progress')
  const solved = data.exercises.filter((e) => e.status === 'solved')

  return (
    <div className="subview">
      <h1>Your projects</h1>
      <p className="muted">Everything you&rsquo;ve opened, newest work first.</p>

      {inProgress.length === 0 && solved.length === 0 && (
        <p className="panel muted">
          Nothing on the go yet. Head to <strong>Home</strong> and pick a topic.
        </p>
      )}

      {inProgress.length > 0 && (
        <section>
          <h2>In progress</h2>
          <div className="project-grid">
            {inProgress.map((ex) => (
              <Link key={ex.id} to={`/exercise/${ex.slug}`} className="project-card wip">
                <span className="project-mark" aria-hidden>◐</span>
                <span className="project-title">{ex.title}</span>
                <span className="muted small">
                  {ex.attempts} {ex.attempts === 1 ? 'try' : 'tries'} so far
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {solved.length > 0 && (
        <section>
          <h2>Finished</h2>
          <div className="project-grid">
            {solved.map((ex) => (
              <Link key={ex.id} to={`/exercise/${ex.slug}`} className="project-card done">
                <span className="project-mark" aria-hidden>✓</span>
                <span className="project-title">{ex.title}</span>
                <span className="muted small">solved</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <p className="subview-foot">
        <Link className="link" to="/portfolio">
          Open your full portfolio — code, reflections and all →
        </Link>
      </p>
    </div>
  )
}

// --- Progress & goals ------------------------------------------------------

function ProgressView({ data }: { data: Dashboard }) {
  const { solved, total_exercises: total } = data
  const pct = total ? Math.round((solved / total) * 100) : 0
  const nextUp = data.exercises.find((e) => e.slug === data.continue_slug)

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
