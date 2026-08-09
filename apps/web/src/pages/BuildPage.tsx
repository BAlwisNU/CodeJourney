import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { api } from '../lib/api'
import type { Project } from '../lib/types'

/**
 * The build: the part the lessons were for.
 *
 * Until now the platform taught the pieces and then stopped. You could finish
 * every lesson a project needed and there was nowhere to go and actually make
 * the thing -- which left the project as a label on a progress bar rather than
 * something anyone ever built.
 *
 * Deliberately not another exercise. There is no starter file, no tests and no
 * grader, because the difference between the last lesson and this is exactly
 * that nobody is checking: you decide when it works. What the page offers is
 * the brief, what you already know how to do, and somewhere to say you have
 * done it.
 */
export function BuildPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .projects()
      .then((r) => {
        if (cancelled) return
        const found = r.projects.find((p) => p.id === id)
        if (!found) setError('That project is not on your list.')
        else setProject(found)
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      cancelled = true
    }
  }, [id])

  if (error) return <p className="panel panel-error">{error}</p>
  if (!project) return <p className="muted">Loading…</p>

  const learned = project.lessons.filter(
    (l) => l.status === 'solved' || l.status === 'known'
  )
  const left = project.lessons.filter(
    (l) => l.status !== 'solved' && l.status !== 'known'
  )

  async function toggleBuilt() {
    setBusy(true)
    try {
      setProject(await api.setProjectBuilt(project!.id, !project!.built))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="build">
      <header className="build-head">
        <Link className="reflect-back" to="/exercises">
          ← Back to your projects
        </Link>
        <p className="eyebrow">Build it</p>
        <h1>{project.title}</h1>
        {project.blurb && <p className="build-brief">{project.blurb}</p>}
      </header>

      <section className="panel build-ready">
        <h2>What you can already do</h2>
        <p className="muted small">
          Every one of these is a piece of the thing you are about to make.
        </p>
        <ul className="build-list">
          {learned.map((l) => (
            <li key={l.slug}>
              <span aria-hidden>✓</span>
              <Link to={`/exercise/${l.slug}/plan`}>{l.title}</Link>
            </li>
          ))}
          {learned.length === 0 && (
            <li className="muted">Nothing yet — the lessons come first.</li>
          )}
        </ul>
      </section>

      {left.length > 0 && (
        <section className="panel build-left">
          <h2>Still to learn</h2>
          <p className="muted small">
            You can start building without these. They are the parts you would
            otherwise have to look up.
          </p>
          <ul className="build-list">
            {left.map((l) => (
              <li key={l.slug}>
                <span aria-hidden>·</span>
                <Link to={`/exercise/${l.slug}/plan`}>{l.title}</Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="panel build-go">
        <h2>Now make it</h2>
        <p>
          Open an editor — the one here, or anything on your own machine — and
          build it for real. Nothing marks this and nothing tests it. It is
          finished when you say it is.
        </p>
        <div className="build-actions">
          <button className="primary" onClick={() => void toggleBuilt()} disabled={busy}>
            {busy ? 'Saving…' : project.built ? 'Not finished after all' : 'I built it'}
          </button>
          <button type="button" className="linkish" onClick={() => navigate('/exercises')}>
            Back to your projects
          </button>
        </div>
        {project.built && (
          <p className="build-done">
            Marked as built. That is a thing you made that did not exist before.
          </p>
        )}
      </section>
    </div>
  )
}
