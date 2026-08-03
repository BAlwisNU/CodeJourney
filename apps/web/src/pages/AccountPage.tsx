import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api, token } from '../lib/api'
import type { Account, LearnerProfile, OnboardingPlan } from '../lib/types'

/**
 * Account settings, which in practice means one thing: consent.
 *
 * Withdrawing has to be as easy as granting, and visible without asking anyone.
 * A right to withdraw that requires emailing a researcher is a right on paper
 * only, and it is the first participant protection an ethics committee looks for.
 */
export function AccountPage() {
  const navigate = useNavigate()
  const [account, setAccount] = useState<Account | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [justChanged, setJustChanged] = useState(false)

  useEffect(() => {
    api
      .me()
      .then(setAccount)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  async function toggleConsent(next: boolean) {
    setBusy(true)
    setJustChanged(false)
    try {
      setAccount(await api.setConsent(next))
      setJustChanged(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  if (error) return <p className="panel panel-error">{error}</p>
  if (!account) return <p className="muted">Loading…</p>

  const consenting = account.consented_at !== null

  return (
    <div className="dash">
      <header className="dash-head">
        <div>
          <h1>Your account</h1>
          <p className="muted">{account.email}</p>
        </div>
        <Link className="link" to="/exercises">
          Back to your work
        </Link>
      </header>

      <section className="panel">
        <h2>Name</h2>
        <p className="muted">{account.display_name}</p>
      </section>

      <LearnerProfilePanel />

      <OnboardingPlanPanel />

      <section className="panel">
        <h2>Helping with the research</h2>

        <p className="muted">
          CodeJourney is a student project studying whether exercises about your
          own life help people learn to code. Taking part means your exercise
          attempts can be used, anonymously, in that research.
        </p>

        <ul className="honest-list">
          <li>
            <strong>Your journal is never included</strong>, and is never read by
            an AI.
          </li>
          <li>
            <strong>The site works exactly the same either way.</strong> Nothing
            is withheld if you opt out.
          </li>
          <li>
            <strong>You can change your mind at any time</strong>, right here.
            Opting out later doesn&rsquo;t delete your work or your progress.
          </li>
        </ul>

        <div className="consent-state">
          <p>
            {consenting ? (
              <>
                <span className="dot dot-on" aria-hidden /> You&rsquo;re currently
                taking part.
              </>
            ) : (
              <>
                <span className="dot" aria-hidden /> You&rsquo;re not taking part.
              </>
            )}
          </p>

          <button
            className={consenting ? '' : 'primary'}
            onClick={() => toggleConsent(!consenting)}
            disabled={busy}
          >
            {busy
              ? 'One sec…'
              : consenting
                ? 'Withdraw from the research'
                : 'Take part in the research'}
          </button>
        </div>

        {justChanged && (
          <p className="muted small">
            {consenting
              ? 'Thank you — your attempts can now be included.'
              : 'Done. Your data will not be used in the research. Everything you have made is still here.'}
          </p>
        )}
      </section>

      <section className="panel">
        <h2>Signing out</h2>
        <p className="muted small">
          Your work is saved on our server, not in this browser, so you can log
          back in anywhere and pick up where you left off.
        </p>
        <button
          onClick={() => {
            token.clear()
            navigate('/')
          }}
        >
          Log out
        </button>
      </section>
    </div>
  )
}

/**
 * What the learner said they were here for, back where they can change it.
 *
 * Two of the three welcome-step answers appear: goals and project ideas. How
 * much programming they said they had done is deliberately not here, and the
 * API has no way to return it -- see LearnerProfileOut in schemas.py. Editing
 * saving here sends only those two, and the API leaves anything it wasn't given
 * alone. That is load-bearing: this page cannot read the experience answer, so
 * a whole-row replace would erase it every time someone edited a goal.
 */
function LearnerProfilePanel() {
  const [profile, setProfile] = useState<LearnerProfile | null>(null)
  const [goals, setGoals] = useState('')
  const [ideas, setIdeas] = useState('')
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api
      .learnerProfile()
      .then((result) => {
        setProfile(result)
        setGoals(result.goals)
        setIdeas(result.project_ideas)
      })
      // Silent: this panel is not why anyone came to the account page, and a
      // red banner over the consent controls would be worse than its absence.
      .catch(() => setProfile(null))
  }, [])

  async function save() {
    setBusy(true)
    setError(null)
    try {
      // Only the two fields this form owns. Omitted fields are left untouched
      // by the API, which is the only reason editing a goal here doesn't wipe
      // the experience answer -- this page cannot read it to send it back.
      const next = await api.saveLearnerProfile({
        goals: goals.trim(),
        project_ideas: ideas.trim(),
      })
      setProfile(next)
      setEditing(false)
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  if (!profile) return null

  return (
    <section className="panel">
      <h2>What you&rsquo;re here for</h2>
      <p className="muted small">
        Used to tailor your lessons and examples. Only you can see this.
      </p>

      {error && <p className="panel panel-error small">{error}</p>}

      {editing ? (
        <>
          <label className="field">
            What would you like to be able to do?
            <textarea
              value={goals}
              onChange={(e) => setGoals(e.target.value)}
              rows={3}
              maxLength={2000}
            />
          </label>
          <label className="field">
            Anything you already want to build?
            <textarea
              value={ideas}
              onChange={(e) => setIdeas(e.target.value)}
              rows={3}
              maxLength={2000}
            />
          </label>
          <div className="actions">
            <button className="primary" onClick={save} disabled={busy}>
              {busy ? 'Saving…' : 'Save'}
            </button>
            <button
              className="linkish"
              onClick={() => {
                setGoals(profile.goals)
                setIdeas(profile.project_ideas)
                setEditing(false)
              }}
              disabled={busy}
            >
              Cancel
            </button>
          </div>
        </>
      ) : (
        <>
          <dl className="profile-answers">
            <dt>Goals</dt>
            <dd className={profile.goals ? '' : 'muted'}>
              {profile.goals || 'Not said yet.'}
            </dd>
            <dt>Project ideas</dt>
            <dd className={profile.project_ideas ? '' : 'muted'}>
              {profile.project_ideas || 'Not said yet.'}
            </dd>
          </dl>
          <div className="actions">
            <button onClick={() => setEditing(true)}>Edit</button>
            {saved && <span className="muted small">Saved.</span>}
          </div>
        </>
      )}
    </section>
  )
}

const PLAN_TOPIC_LABELS: Record<string, string> = {
  lists: 'Lists',
  dicts: 'Dictionaries',
  loops: 'Loops',
  strings: 'Strings',
  functions: 'Functions',
  file_io: 'Files',
}

/**
 * What the welcome chat concluded, read-only.
 *
 * Not editable, unlike the panel above, and the difference is deliberate: that
 * one holds the learner's own words and is theirs to rewrite. This is a model's
 * reading of a conversation, and quietly editing it would make it look like
 * something they had said. If it's wrong, the fix is to talk to the tutor
 * again, not to rewrite the transcript's conclusions.
 *
 * Renders nothing at all until a plan exists, so anyone who skipped the chat
 * never sees an empty box asking why it's empty.
 */
function OnboardingPlanPanel() {
  const [plan, setPlan] = useState<OnboardingPlan | null>(null)

  useEffect(() => {
    api
      .onboardingPlan()
      .then(setPlan)
      .catch(() => setPlan(null))
  }, [])

  if (!plan?.recorded) return null

  return (
    <section className="panel">
      <h2>What you said you wanted to build</h2>
      <p className="muted small">
        From your welcome chat. Used to pick the examples and practice you get.
      </p>

      {plan.interests && <p className="wc-interests">{plan.interests}</p>}

      {plan.topics.length > 0 && (
        <>
          <h3 className="plan-subhead">Good places to start</h3>
          <ul className="wc-topics">
            {plan.topics.map((topic) => (
              <li key={topic}>{PLAN_TOPIC_LABELS[topic] ?? topic}</li>
            ))}
          </ul>
        </>
      )}

      {plan.projects.length > 0 && (
        <>
          <h3 className="plan-subhead">Things you could build</h3>
          <ul className="wc-projects">
            {plan.projects.map((project) => (
              <li key={project.title}>
                <strong>{project.title}</strong>
                <span>{project.blurb}</span>
                {project.topics.length > 0 && (
                  <span className="wc-project-topics">
                    {project.topics
                      .map((t) => PLAN_TOPIC_LABELS[t] ?? t)
                      .join(' \u00b7 ')}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
