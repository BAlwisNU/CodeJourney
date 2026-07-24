import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { FlowNav } from '../components/FlowNav'
import { api, token } from '../lib/api'
import type { Dashboard, ExerciseProgress } from '../lib/types'

const CONCEPT_LABELS: Record<string, string> = {
  lists: 'Lists',
  dicts: 'Dictionaries',
  loops: 'Loops',
  strings: 'Strings',
  functions: 'Functions',
  file_io: 'Files',
}

const THEME_LABELS: Record<string, string> = {
  games: 'Games & quests',
  sports: 'Sports & leagues',
  space: 'Space missions',
  music: 'Music & playlists',
  stories: 'Stories & words',
  generic: 'Plain practice',
}

const THEME_ICONS: Record<string, string> = {
  games: '🎮',
  sports: '🏆',
  space: '🚀',
  music: '🎧',
  stories: '📖',
  generic: '📋',
}

const THEME_BLURBS: Record<string, string> = {
  games: 'Quests, inventories and scores — records with state.',
  sports: 'Leagues, tallies and tables — grouping and totals.',
  space: 'Missions, waypoints and fuel — sequences in order.',
  music: 'Playlists, sets and overlaps — pairings and patterns.',
  stories: 'Word games and generators — making and changing text.',
  generic: 'The same problems with the world stripped out.',
}

const STATUS_LABELS: Record<ExerciseProgress['status'], string> = {
  solved: 'Done',
  in_progress: 'In progress',
  not_started: 'Not started',
}

export function DashboardPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<Dashboard | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .progress()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  function logOut() {
    token.clear()
    navigate('/')
  }

  if (error) return <p className="panel panel-error">{error}</p>
  if (!data) return <p className="muted">Loading…</p>

  const { solved, total_exercises: total } = data
  const percent = total === 0 ? 0 : Math.round((solved / total) * 100)
  const nothingYet = data.total_attempts === 0
  const nextUp = data.exercises.find((e) => e.slug === data.continue_slug)

  return (
    <div className="dash">
      <FlowNav current="connect" />

      <header className="dash-head">
        <div>
          <h1>
            {nothingYet ? 'Welcome' : 'Welcome back'}, {data.display_name}
          </h1>
          <p className="muted">
            {nothingYet
              ? 'Pick something below and write your first program. You can try as many times as you like.'
              : `You've solved ${solved} of ${total}.`}
          </p>
        </div>
        <nav className="dash-nav">
          <Link className="link" to="/portfolio">
            Portfolio
          </Link>
          {data.role === 'instructor' && (
            <Link className="link" to="/instructor">
              Class
            </Link>
          )}
          <Link className="link" to="/account">
            Account
          </Link>
          <button className="link" onClick={logOut}>
            Log out
          </button>
        </nav>
      </header>

      {/* Pick-up-where-you-left-off. Re-finding your place in a list is friction
          for no reason, and this is the action almost everyone wants. */}
      {nextUp && (
        <section className="panel next-up">
          <div>
            <p className="eyebrow">
              {nextUp.status === 'in_progress' ? 'Carry on with' : 'Start with'}
            </p>
            <h2>{nextUp.title}</h2>
            <p className="muted small">
              {CONCEPT_LABELS[nextUp.concept] ?? nextUp.concept}
              {nextUp.attempts > 0 &&
                ` · ${nextUp.attempts} ${nextUp.attempts === 1 ? 'try' : 'tries'} so far`}
            </p>
          </div>
          <Link
            className="btn btn-primary"
            // Unstarted exercises go via Plan (lesson, quiz, warm-up); ones
            // already in progress go straight back to the code, because
            // re-reading the lesson isn't what someone mid-attempt wants.
            to={
              nextUp.status === 'in_progress'
                ? `/exercise/${nextUp.slug}`
                : `/exercise/${nextUp.slug}/plan`
            }
          >
            {nextUp.status === 'in_progress' ? 'Carry on' : 'Start'}
          </Link>
        </section>
      )}

      {/* A progress bar, and nothing more. Points, badges and streaks were cut
          on purpose: lots of code, thin pedagogical value, and nothing to write
          about in the report. See README, "Deliberately not built". */}
      <section className="panel">
        <div className="progress-head">
          <h2>Your progress</h2>
          <span className="muted small">
            {solved} of {total} solved
          </span>
        </div>
        <div
          className="bar"
          role="progressbar"
          aria-valuenow={solved}
          aria-valuemin={0}
          aria-valuemax={total}
          aria-label={`${solved} of ${total} exercises solved`}
        >
          <span style={{ width: `${percent}%` }} />
        </div>

        {/* Only worth showing once there's more than one concept -- with a single
            concept this bar is a pixel-identical copy of the one above it. It
            becomes useful as the exercise set fills out across the 6 concepts. */}
        {data.concepts.length > 1 && (
          <ul className="concepts">
            {data.concepts.map((concept) => (
              <li key={concept.concept}>
                <span className="concept-name">
                  {CONCEPT_LABELS[concept.concept] ?? concept.concept}
                </span>
                <span className="muted small">
                  {concept.solved}/{concept.total}
                </span>
                <div className="bar bar-sm">
                  <span
                    style={{
                      width: `${concept.total ? (concept.solved / concept.total) * 100 : 0}%`,
                    }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Stage 1 -- Connect. Themes are the entry point the proposal describes:
          you choose what the project is ABOUT, and that choice changes the kind
          of program you write, not just its variable names. */}
      <section className="panel">
        <h2>Choose what to work on</h2>
        <p className="muted small">
          Each theme leads to a different kind of program. Pick whichever you
          actually care about — you can make the details up.
        </p>
        <div className="themes-pick">
          {Object.entries(
            data.exercises.reduce<Record<string, typeof data.exercises>>(
              (acc, ex) => {
                ;(acc[ex.theme] ||= []).push(ex)
                return acc
              },
              {}
            )
          ).map(([theme, items]) => (
            <article key={theme} className="theme-card">
              <h3>
                <span className="world-icon" aria-hidden>
                  {THEME_ICONS[theme] ?? '•'}
                </span>{' '}
                {THEME_LABELS[theme] ?? theme}
              </h3>
              <p className="muted small">{THEME_BLURBS[theme] ?? ''}</p>
              <ul>
                {items.map((ex) => (
                  <li key={ex.id}>
                    <Link to={`/exercise/${ex.slug}/plan`}>{ex.title}</Link>
                    {ex.status === 'solved' && (
                      <span className="badge badge-done">done</span>
                    )}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Everything</h2>
        <ul className="ex-list">
          {data.exercises.map((exercise) => (
            <li key={exercise.id} className={`ex ex-${exercise.status}`}>
              <span className="ex-mark" aria-hidden>
                {exercise.status === 'solved' ? '✓' : exercise.status === 'in_progress' ? '·' : ''}
              </span>
              <Link to={`/exercise/${exercise.slug}`} className="ex-title">
                {exercise.title}
              </Link>
              <span className="badge">
                {CONCEPT_LABELS[exercise.concept] ?? exercise.concept}
              </span>
              {/* The condition label is visible because hiding it would be the
                  deception, not the disclosure -- participants consent to a
                  study that compares two kinds of exercise. */}
              {exercise.variant === 'generic' && (
                <span className="badge badge-quiet">plain</span>
              )}
              <span className="ex-status muted small">
                {STATUS_LABELS[exercise.status]}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
