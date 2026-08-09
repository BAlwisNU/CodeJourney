import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../lib/api'

/**
 * Step two of signing up: what do you want out of this, and what is in the way?
 *
 * Written for somebody who has never programmed, which changes what is worth
 * asking. The old version asked three open questions, two of which a complete
 * beginner cannot answer -- "what would you like to be able to do?" and "what
 * do you want to build?" both assume you already know what is buildable. A
 * blank box is the most intimidating control on a form, and the people most
 * likely to leave it empty are exactly the ones the answers would help most.
 *
 * So most of this is now one tap. Suggestion chips fill the two text boxes in,
 * because recognising something you want is far easier than inventing it from
 * nothing, and the chips double as an answer to "what is even possible here?".
 * Every box is still there for anyone who would rather write.
 *
 * The question that earns its place most is the one nobody asks: what is
 * putting you off. What stops a beginner is almost never syntax -- it is
 * believing they are not a maths person, or not knowing what to learn first. A
 * coach told that can address the belief instead of teaching over the top of
 * it.
 *
 * This sits between someone pressing "Create account" and the thing they came
 * for, which is where a signup funnel loses people. So: everything optional,
 * "Skip for now" a real button, nothing here blocks.
 *
 * Two questions, and it fits on one screen again.
 *
 * It had six. They were all useful and it was still wrong: this sits between
 * someone pressing "Create account" and the thing they came for, and length
 * here is paid for in people who never arrive. What you want to build and how
 * much you have done are the two that change the teaching from the very first
 * lesson, so they stay.
 *
 * The rest -- what is putting you off, how much time you have, how you like to
 * learn -- are not gone, they are asked later, in the place where the answer
 * would actually be used. A question about time means something when you are
 * choosing what to do next; on a signup form it is a survey.
 *
 * What happens to the answers is stated on the page rather than buried in a
 * policy. Goals and project ideas come back on the account page and are theirs
 * to edit; the rest are asked once, to pitch the teaching, and never read back.
 */

const EXPERIENCE = [
  { key: 'none', label: 'Never written code before' },
  { key: 'some_python', label: 'Tried a bit of Python before' },
  { key: 'other_language', label: 'Comfortable in another language, new to Python' },
  { key: 'rusty', label: "Learnt some once, but it's rusty" },
]




// The chips under the two open questions. Examples, not options: they append
// to the box, so several can be combined and then edited.
/** Things to build, mirroring STARTER_PROJECTS in apps/api/app/models.py.
 *
 *  Picking one is the whole point of this step now: a project is what the
 *  dashboard is organised around, so the fastest way to a page that means
 *  something is to leave here having chosen one. Recognition again -- a
 *  beginner cannot answer "what would you like to build?" from nothing, but
 *  can absolutely point at the one that sounds fun. */
const STARTERS = [
  { title: 'A quest log', topics: ['lists', 'dicts', 'loops'],
    blurb: 'Track what you have to do, what is overdue, and what is done.' },
  { title: 'A word game like Wordle', topics: ['strings', 'lists', 'loops'],
    blurb: 'Guess a word, colour the letters, keep the score.' },
  { title: 'A tracker for your runs', topics: ['file_io', 'lists', 'functions'],
    blurb: 'Read your times from a file and work out how you are doing.' },
]

const GOAL_EXAMPLES = [
  'Automate the boring parts of my job',
  'Understand what my team is building',
  'Get through my course',
  'Change career',
  'Make something of my own',
]

const BUILD_EXAMPLES = [
  'A bot for my group chat',
  'A tracker for my running times',
  'A game like Wordle',
  'Something to sort my photos',
  'No idea yet',
]

export function WelcomePage() {
  const navigate = useNavigate()

  const [picked, setPicked] = useState<number | null>(null)
  const [goals, setGoals] = useState('')
  const [experience, setExperience] = useState('')
  const [experienceNote, setExperienceNote] = useState('')
  const [projectIdeas, setProjectIdeas] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /** Append an example rather than replacing what is there. */
  const addExample = (
    value: string,
    current: string,
    setter: (next: string) => void
  ) => {
    if (current.toLowerCase().includes(value.toLowerCase())) return
    setter(current.trim() ? `${current.replace(/[.,\s]+$/, '')}, ${value}` : value)
  }


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
      // A picked project is created here rather than inferred later, so the
      // dashboard has something on it the moment they arrive.
      if (picked !== null) {
        const s = STARTERS[picked]
        await api.addProject({ title: s.title, blurb: s.blurb, topics: s.topics })
      }
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
      <h1>Tell us where you&rsquo;re starting from</h1>
      <p className="muted">
        Pick something to build and we will work out the lessons for it. Both
        questions are optional, and nobody else sees your answers.
      </p>

      {error && <p className="panel panel-error small">{error}</p>}

      <fieldset className="welcome-choices">
        <legend>Which of these would you like to build?</legend>
        <div className="starters">
          {STARTERS.map((s, i) => (
            <button
              key={s.title}
              type="button"
              className={picked === i ? 'starter is-on' : 'starter'}
              aria-pressed={picked === i}
              onClick={() => setPicked(picked === i ? null : i)}
            >
              <strong>{s.title}</strong>
              <span>{s.blurb}</span>
            </button>
          ))}
        </div>
        <p className="field-hint">
          You can change it, or add others, whenever you like.
        </p>
      </fieldset>

      <label className="field">
        What would you like to be able to do?
        <textarea
          value={goals}
          onChange={(e) => setGoals(e.target.value)}
          rows={2}
          maxLength={2000}
          placeholder="In your own words…"
          autoFocus
        />
      </label>
      <div className="chips chips-add" role="group" aria-label="Example goals">
        {GOAL_EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            className="chip"
            onClick={() => addExample(example, goals, setGoals)}
          >
            + {example}
          </button>
        ))}
      </div>

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
          rows={2}
          maxLength={2000}
          placeholder="Even a vague idea helps — practice can be built around it."
        />
      </label>
      <div className="chips chips-add" role="group" aria-label="Example things to build">
        {BUILD_EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            className="chip"
            onClick={() => addExample(example, projectIdeas, setProjectIdeas)}
          >
            + {example}
          </button>
        ))}
      </div>

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
