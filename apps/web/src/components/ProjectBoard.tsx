import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { Project } from '../lib/types'

/**
 * What you are building, and what is left to learn before you can.
 *
 * The dashboard's main view. It replaces six near-identical rows of the whole
 * syllabus with one card per thing the learner actually wants to make -- each
 * carrying the lessons it needs as a checklist. The curriculum has not gone
 * anywhere; it is what the checklists are made of. It is just no longer the
 * thing you are asked to navigate.
 *
 * A lesson can be marked "I already know this" from here. Someone arriving
 * with experience should be able to clear the parts they have done and get to
 * the part of their project that is new, and doing that from the checklist --
 * where they can see what it unblocks -- is the only place it makes sense.
 */

const STATUS_LABEL: Record<string, string> = {
  solved: 'done',
  in_progress: 'in progress',
  known: 'you know this',
  not_started: '',
}

function ProjectCard({
  project,
  onChanged,
}: {
  project: Project
  onChanged: (next: Project) => void
}) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const complete = project.total > 0 && project.done === project.total

  async function toggleKnown(slug: string, known: boolean) {
    setBusy(slug)
    try {
      await api.setLessonKnown(slug, known)
      const { projects } = await api.projects()
      const fresh = projects.find((p) => p.id === project.id)
      if (fresh) onChanged(fresh)
    } finally {
      setBusy(null)
    }
  }

  async function toggleBuilt() {
    setBusy('built')
    try {
      onChanged(await api.setProjectBuilt(project.id, !project.built))
    } finally {
      setBusy(null)
    }
  }

  return (
    <article className={project.built ? 'proj is-built' : 'proj'}>
      <header className="proj-head">
        <div>
          <h3>{project.title}</h3>
          {project.blurb && <p className="proj-blurb">{project.blurb}</p>}
        </div>
        {project.built && <span className="proj-flag">Built</span>}
      </header>

      {/* Progress as parts of a thing, not as a percentage of a syllabus. */}
      <div className="proj-bar" aria-hidden>
        <span style={{ width: `${project.total ? (project.done / project.total) * 100 : 0}%` }} />
      </div>
      <p className="proj-count muted small">
        {project.done} of {project.total} pieces ready
      </p>

      <div className="proj-actions">
        {project.next_slug ? (
          <Link className="btn btn-primary" to={`/exercise/${project.next_slug}/plan`}>
            {project.done === 0 ? 'Start the first piece' : 'Carry on'} →
          </Link>
        ) : (
          // Every piece is cleared, so the only thing left is the thing itself.
          <Link className="btn btn-primary" to={`/build/${project.id}`}>
            Build it →
          </Link>
        )}
        <button type="button" className="linkish" onClick={() => setOpen((v) => !v)}>
          {open ? 'Hide the pieces' : `${project.total} pieces`}
        </button>
        {complete && (
          <button type="button" className="linkish" onClick={() => void toggleBuilt()} disabled={busy === 'built'}>
            {project.built ? 'Not built yet' : 'Mark as built'}
          </button>
        )}
      </div>

      {open && (
        <ol className="proj-lessons">
          {project.lessons.map((lesson) => (
            <li key={lesson.slug} className={`proj-lesson is-${lesson.status}`}>
              <Link to={`/exercise/${lesson.slug}/plan`}>
                <span className="proj-lesson-title">{lesson.title}</span>
                <span className="proj-lesson-concept">{lesson.concept}</span>
              </Link>
              {STATUS_LABEL[lesson.status] && (
                <span className="proj-lesson-state">{STATUS_LABEL[lesson.status]}</span>
              )}
              {lesson.status !== 'solved' && (
                <button
                  type="button"
                  className="proj-known"
                  disabled={busy === lesson.slug}
                  onClick={() => void toggleKnown(lesson.slug, lesson.status !== 'known')}
                >
                  {lesson.status === 'known' ? 'Actually, teach me' : 'I know this'}
                </button>
              )}
            </li>
          ))}
        </ol>
      )}
    </article>
  )
}

export function ProjectBoard() {
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .projects()
      .then((r) => !cancelled && setProjects(r.projects))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      cancelled = true
    }
  }, [])

  if (error) return <p className="panel panel-error">{error}</p>
  if (!projects) return <p className="muted">Loading…</p>

  const replace = (next: Project) =>
    setProjects((current) =>
      (current ?? []).map((p) => (p.id === next.id ? next : p))
    )

  return (
    <section className="projects">
      <div className="projects-head">
        <h2>What you&rsquo;re building</h2>
        <button type="button" className="linkish" onClick={() => setAdding((v) => !v)}>
          {adding ? 'Never mind' : '+ Something else'}
        </button>
      </div>

      {adding && (
        <NewProjectForm
          onAdded={(p) => {
            setProjects((current) => [...(current ?? []), p])
            setAdding(false)
          }}
        />
      )}

      <div className="projects-grid">
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} onChanged={replace} />
        ))}
      </div>
    </section>
  )
}

/** The six concepts, as things a project might need. */
const TOPICS = [
  { key: 'lists', label: 'Lists' },
  { key: 'loops', label: 'Loops' },
  { key: 'dicts', label: 'Dictionaries' },
  { key: 'strings', label: 'Text' },
  { key: 'functions', label: 'Functions' },
  { key: 'file_io', label: 'Files' },
]

function NewProjectForm({ onAdded }: { onAdded: (p: Project) => void }) {
  const [title, setTitle] = useState('')
  const [topics, setTopics] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function add(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      onAdded(await api.addProject({ title: title.trim(), blurb: '', topics }))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="proj-new" onSubmit={add}>
      <label className="field">
        What do you want to make?
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={200}
          placeholder="A bot for my group chat"
          autoFocus
        />
      </label>
      {/* Picked rather than inferred. Working out which concepts a project
          needs is a job for someone who already knows them, which is exactly
          who this is not for -- so the options are shown and any guess is a
          fine one, because the lessons are the same lessons either way. */}
      <p className="field-hint">Which of these will it need? Guess if you&rsquo;re not sure.</p>
      <div className="chips">
        {TOPICS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={topics.includes(t.key) ? 'chip is-on' : 'chip'}
            aria-pressed={topics.includes(t.key)}
            onClick={() =>
              setTopics((cur) =>
                cur.includes(t.key) ? cur.filter((k) => k !== t.key) : [...cur, t.key]
              )
            }
          >
            {t.label}
          </button>
        ))}
      </div>
      {error && <p className="panel panel-error small">{error}</p>}
      <button className="primary" disabled={busy || !title.trim() || !topics.length}>
        {busy ? 'Adding…' : 'Add it'}
      </button>
    </form>
  )
}
