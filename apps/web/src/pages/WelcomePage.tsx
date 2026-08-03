import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../lib/api'

/**
 * Step two of signing up: what do you want out of this?
 *
 * Three questions, all optional, all skippable. This sits between someone
 * pressing "Create account" and the thing they actually came for, which is a
 * place a signup funnel loses people -- so nothing here is required, "Skip for
 * now" is a real button and not a greyed-out afterthought, and the whole form
 * fits on one screen.
 *
 * What happens to the answers is stated on the page rather than buried in a
 * policy. They are used to tailor lessons, by the same tutor the student can
 * already talk to; saying so is the difference between personalisation and
 * something being done to them. Two of the three come back on the account page
 * where they can be changed; the experience question is asked once, to pitch
 * explanations correctly, and is not read back.
 */

const EXPERIENCE = [
  { key: 'none', label: 'Never written code before' },
  { key: 'some_python', label: 'Tried a bit of Python before' },
  { key: 'other_language', label: 'Comfortable in another language, new to Python' },
  { key: 'rusty', label: "Learnt some once, but it's rusty" },
]

export function WelcomePage() {
  const navigate = useNavigate()

  const [goals, setGoals] = useState('')
  const [experience, setExperience] = useState('')
  const [experienceNote, setExperienceNote] = useState('')
  const [projectIdeas, setProjectIdeas] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function save(answers: {
    goals: string
    experience: string
    experience_note: string
    project_ideas: string
  }) {
    setBusy(true)
    setError(null)
    try {
      await api.saveLearnerProfile(answers)
      navigate('/welcome/chat', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setBusy(false)
    }
  }

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    void save({
      goals: goals.trim(),
      experience,
      experience_note: experienceNote.trim(),
      project_ideas: projectIdeas.trim(),
    })
  }

  // Skipping still writes the (empty) profile. That is what stops us asking
  // again on every visit -- "completed" has to mean "we asked", not "they
  // answered", or skipping would be indistinguishable from never having seen it.
  //
  // It also goes straight in, past the chat. Someone pressing "skip" is telling
  // us they want to get started, not that they'd like a different set of
  // questions.
  const skip = async () => {
    setBusy(true)
    try {
      await api.saveLearnerProfile({
        goals: '',
        experience: '',
        experience_note: '',
        project_ideas: '',
      })
    } catch {
      // Not worth blocking on: the profile row only records that we asked.
    }
    navigate('/exercises', { replace: true })
  }

  return (
    <form className="welcome" onSubmit={submit} noValidate>
      <p className="eyebrow">Step 2 of 3</p>
      <h1>Tell us what you&rsquo;re here for</h1>
      <p className="muted">
        Three questions, all optional. Your answers are used to tailor the
        lessons and examples you get, and to help the tutor pitch things at the
        right level — they aren&rsquo;t shown to anyone else.
      </p>

      {error && <p className="panel panel-error small">{error}</p>}

      <label className="field">
        What would you like to be able to do?
        <textarea
          value={goals}
          onChange={(e) => setGoals(e.target.value)}
          rows={3}
          maxLength={2000}
          placeholder="Automate the boring parts of my job, understand what my team is building, get through my course…"
          autoFocus
        />
        <span className="field-hint">
          You can change this later on your account page.
        </span>
      </label>

      {/* Not `.field` -- that class styles every input inside it as a
          full-width text box, which turns a radio into a 100%-wide rounded
          rectangle and throws its label off the side of the page. */}
      <fieldset className="welcome-choices">
        <legend>How much programming have you done?</legend>
        {EXPERIENCE.map((option) => (
          <label key={option.key} className="welcome-choice">
            <input
              type="radio"
              name="experience"
              value={option.key}
              checked={experience === option.key}
              onChange={() => setExperience(option.key)}
            />
            <span>{option.label}</span>
          </label>
        ))}
        <input
          className="welcome-note"
          value={experienceNote}
          onChange={(e) => setExperienceNote(e.target.value)}
          maxLength={1000}
          placeholder="Anything else about where you're starting from (optional)"
          aria-label="Anything else about where you're starting from"
        />
      </fieldset>

      <label className="field">
        Anything you already want to build?
        <textarea
          value={projectIdeas}
          onChange={(e) => setProjectIdeas(e.target.value)}
          rows={3}
          maxLength={2000}
          placeholder="A bot for my group chat, a tracker for my running times, a game like Wordle…"
        />
        <span className="field-hint">
          Even a vague idea helps — practice exercises can be built around it.
        </span>
      </label>

      <div className="welcome-actions">
        <button className="primary" disabled={busy}>
          {busy ? 'Saving…' : 'Continue'}
        </button>
        <button
          type="button"
          className="linkish"
          onClick={() => void skip()}
          disabled={busy}
        >
          Skip for now
        </button>
      </div>
    </form>
  )
}
