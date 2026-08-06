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
 * It no longer fits on one screen, which the previous version did and said so.
 * That is the deliberate trade: three of the four added questions are a single
 * tap, so this is quicker to complete than the old three-textarea form even
 * though it is taller to look at. If it ever costs completions, the two open
 * questions are what to cut -- the chips are the cheap part.
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

// Keys must match ONBOARDING_WORRIES and friends in apps/api/app/models.py.
// The server rejects anything it does not recognise rather than dropping it
// quietly, so a drift here fails loudly instead of leaving the coach uninformed.
const WORRIES = [
  { key: 'maths', label: "I'm not a maths person" },
  { key: 'stuck', label: 'Getting stuck and giving up' },
  { key: 'late', label: "I've left it too late" },
  { key: 'where', label: 'Not knowing what to learn first' },
  { key: 'time', label: 'Finding the time' },
  { key: 'asking', label: 'Feeling silly asking questions' },
  { key: 'none', label: 'Nothing much, honestly' },
]

const TIME = [
  { key: 'minutes', label: 'A few minutes here and there' },
  { key: 'hour', label: 'About an hour a week' },
  { key: 'few_hours', label: 'A few hours a week' },
  { key: 'most_days', label: 'Most days' },
]

const LEARN_STYLE = [
  { key: 'read', label: 'Reading it through' },
  { key: 'watch', label: 'Watching someone do it' },
  { key: 'do', label: 'Trying it and breaking it' },
  { key: 'mix', label: 'A bit of everything' },
]

// The chips under the two open questions. Examples, not options: they append
// to the box, so several can be combined and then edited.
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

  const [goals, setGoals] = useState('')
  const [experience, setExperience] = useState('')
  const [experienceNote, setExperienceNote] = useState('')
  const [projectIdeas, setProjectIdeas] = useState('')
  const [worries, setWorries] = useState<string[]>([])
  const [timeAvailable, setTimeAvailable] = useState('')
  const [learnStyle, setLearnStyle] = useState('')
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

  const toggleWorry = (key: string) =>
    setWorries((current) => {
      // "Nothing much" excludes the others in both directions. A form that
      // lets you say you are worried about nothing *and* about maths is a form
      // that was not paying attention.
      if (key === 'none') return current.includes('none') ? [] : ['none']
      const without = current.filter((k) => k !== 'none')
      return without.includes(key)
        ? without.filter((k) => k !== key)
        : [...without, key]
    })

  async function save(answers: {
    goals: string
    experience: string
    experience_note: string
    project_ideas: string
    worries: string[]
    time_available: string
    learn_style: string
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
      worries,
      time_available: timeAvailable,
      learn_style: learnStyle,
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
        worries: [],
        time_available: '',
        learn_style: '',
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
        Every question is optional and most are one tap. Your answers shape the
        lessons and examples you get, and help your coach pitch things at the
        right level — nobody else sees them.
      </p>

      {error && <p className="panel panel-error small">{error}</p>}

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

      <fieldset className="welcome-choices">
        <legend>Is anything putting you off? Pick any that ring true.</legend>
        <div className="chips">
          {WORRIES.map((option) => (
            <button
              key={option.key}
              type="button"
              className={worries.includes(option.key) ? 'chip is-on' : 'chip'}
              aria-pressed={worries.includes(option.key)}
              onClick={() => toggleWorry(option.key)}
            >
              {option.label}
            </button>
          ))}
        </div>
        <p className="field-hint">
          Every one of these is normal, and none of them means you can&rsquo;t do
          this. Saying so just means we can help with it.
        </p>
      </fieldset>

      <fieldset className="welcome-choices">
        <legend>How much time do you realistically have?</legend>
        <div className="chips">
          {TIME.map((option) => (
            <button
              key={option.key}
              type="button"
              className={timeAvailable === option.key ? 'chip is-on' : 'chip'}
              aria-pressed={timeAvailable === option.key}
              onClick={() =>
                setTimeAvailable(timeAvailable === option.key ? '' : option.key)
              }
            >
              {option.label}
            </button>
          ))}
        </div>
        <p className="field-hint">
          There is no right answer. A few minutes at a time is genuinely enough.
        </p>
      </fieldset>

      <fieldset className="welcome-choices">
        <legend>When something is new, what helps most?</legend>
        <div className="chips">
          {LEARN_STYLE.map((option) => (
            <button
              key={option.key}
              type="button"
              className={learnStyle === option.key ? 'chip is-on' : 'chip'}
              aria-pressed={learnStyle === option.key}
              onClick={() =>
                setLearnStyle(learnStyle === option.key ? '' : option.key)
              }
            >
              {option.label}
            </button>
          ))}
        </div>
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
