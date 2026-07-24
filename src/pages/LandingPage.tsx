import { useState } from 'react'
import { Link } from 'react-router-dom'

import { ErrorDemo } from '../components/ErrorDemo'
import { token } from '../lib/api'

/**
 * The public front door.
 *
 * The pitch is the experience: you write real Python about things worth
 * building, it runs the instant you press a key, and when it breaks the site
 * explains why instead of showing you a wall of red.
 *
 * Everything claimed here is something the platform actually does. The demo
 * translations are the literal output of the rule table; the ladder levels and
 * thresholds are the ones in services/hints.py; the worlds are the ones in
 * docs/theme-concept-grid.md. If a claim stops being true, fix the page --
 * overselling is worse than being plain, on a site whose whole promise is that
 * it explains itself honestly.
 */

const WORLDS = [
  {
    key: 'games',
    icon: '🎮',
    name: 'Games & quests',
    shape: 'Records with state',
    example: 'Which quests did you never finish before they expired?',
  },
  {
    key: 'sports',
    icon: '🏆',
    name: 'Sports & leagues',
    shape: 'Grouping and totals',
    example: 'Build the league table from a season of results.',
  },
  {
    key: 'space',
    icon: '🚀',
    name: 'Space missions',
    shape: 'Sequences and order',
    example: 'Plan the fuel stops so the probe actually arrives.',
  },
  {
    key: 'music',
    icon: '🎧',
    name: 'Music & playlists',
    shape: 'Pairings and patterns',
    example: 'Find every track two playlists have in common.',
  },
  {
    key: 'stories',
    icon: '📖',
    name: 'Stories & words',
    shape: 'Making and changing text',
    example: 'A generator that writes a different tale every run.',
  },
]

// Matches DEFAULT_THRESHOLDS in apps/api/app/services/hints.py.
const LADDER = [
  { tag: 'L0', when: 'Instantly', title: 'What actually happened', body: 'Your output, and which checks passed.' },
  { tag: 'L1', when: 'On any error', title: 'The error, in English', body: 'The traceback as a sentence, pointing at the line you wrote — not one inside Python.' },
  { tag: 'L2', when: 'After 2 tries', title: 'Where to look', body: '“Your loop on line 7 never changes i.”' },
  { tag: 'L3', when: 'After 4 tries', title: 'The idea behind it', body: '“A while loop needs something inside it that eventually makes the condition false.”' },
  { tag: 'L4', when: 'After 6 tries', title: 'The shape of it', body: 'A skeleton in plain English. Structure, not code.' },
  { tag: 'L5', when: 'Still stuck', title: 'An actual person', body: 'Your instructor gets told you could use a hand.' },
]

const FEATURES = [
  { icon: '⚡', title: 'Runs as you type', body: 'Python runs inside the browser tab. Press Run and it answers immediately — nothing to install, nothing to wait for.' },
  { icon: '🧩', title: 'Warm up first', body: 'Drag jumbled lines into the right order before facing an empty editor. Two of them don’t belong — spotting that is the puzzle.' },
  { icon: '🔍', title: 'Watch it run', body: 'Step through your program line by line and see exactly what each one does to your data.' },
  { icon: '📓', title: 'Keep the receipts', body: 'What you tried, where you got stuck, how you fixed it — building a portfolio that shows how far you came, not just your final answers.' },
]

export function LandingPage() {
  const signedIn = Boolean(token.get())
  const [openWorld, setOpenWorld] = useState<string | null>('games')

  return (
    <div className="landing">
      <header className="landing-nav">
        <span className="wordmark">
          <span className="mark" aria-hidden>
            {'{ }'}
          </span>
          CodeJourney
        </span>
        <nav>
          {signedIn ? (
            <Link className="btn btn-primary" to="/exercises">
              Keep going
            </Link>
          ) : (
            <>
              <Link className="btn btn-ghost" to="/login">
                Log in
              </Link>
              <Link className="btn btn-primary" to="/signup">
                Start free
              </Link>
            </>
          )}
        </nav>
      </header>

      <section className="hero">
        <p className="eyebrow">
          <span className="pip" aria-hidden /> Python for absolute beginners
        </p>
        <h1>
          Write real code.<br />
          Break it. <span className="grad">Find out why.</span>
        </h1>
        <p className="lede">
          Most people quit programming for the same two reasons: the exercises
          are dull, and when the code breaks all you get is red text and the word{' '}
          <em>wrong</em>. CodeJourney fixes both — you build things worth
          building, and every failure comes with an explanation.
        </p>
        <div className="hero-cta">
          <Link
            className="btn btn-primary btn-lg"
            to={signedIn ? '/exercises' : '/signup'}
          >
            {signedIn ? 'Keep going' : 'Start your first project'}
          </Link>
          <span className="muted small">
            Free · nothing to install · runs in your browser
          </span>
        </div>

        <ul className="hero-stats">
          <li>
            <strong>0</strong>
            <span>things to install</span>
          </li>
          <li>
            <strong>∞</strong>
            <span>tries per exercise</span>
          </li>
          <li>
            <strong>5</strong>
            <span>levels of help</span>
          </li>
          <li>
            <strong>0</strong>
            <span>times we show the answer</span>
          </li>
        </ul>
      </section>

      {/* The proof, and the most persuasive thing on the page: press a button,
          watch a traceback become a sentence. */}
      <section className="band" aria-labelledby="demo-heading">
        <h2 id="demo-heading">Try breaking something</h2>
        <p className="section-lede">
          Pick a mistake everyone makes in their first week, and press Run. This
          is the real translation, word for word.
        </p>
        <ErrorDemo />
      </section>

      <section className="band" aria-labelledby="worlds-heading">
        <h2 id="worlds-heading">Pick a world to build in</h2>
        <p className="section-lede">
          Each one leads to a genuinely different kind of program — different
          data, different shape, different part of Python. Not the same exercise
          with the variables renamed.
        </p>

        <ul className="worlds">
          {WORLDS.map((world) => (
            <li
              key={world.key}
              className={openWorld === world.key ? 'world on' : 'world'}
            >
              <button
                type="button"
                onClick={() =>
                  setOpenWorld(openWorld === world.key ? null : world.key)
                }
                aria-expanded={openWorld === world.key}
              >
                <span className="world-icon" aria-hidden>
                  {world.icon}
                </span>
                <span className="world-name">{world.name}</span>
                <span className="world-shape">{world.shape}</span>
              </button>
              {openWorld === world.key && (
                <p className="world-example">{world.example}</p>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="band" aria-labelledby="ladder-heading">
        <h2 id="ladder-heading">Stuck? Help arrives in steps</h2>
        <p className="section-lede">
          Each rung tells you a little more. Retrying costs you nothing, and the
          last step is a human being — never the answer.
        </p>

        <ol className="ladder">
          {LADDER.map((step) => (
            <li key={step.tag}>
              <span className="rung">{step.tag}</span>
              <div className="rung-body">
                <h3>
                  {step.title} <span className="when">{step.when}</span>
                </h3>
                <p>{step.body}</p>
              </div>
            </li>
          ))}
          <li className="never">
            <span className="rung rung-never">✕</span>
            <div className="rung-body">
              <h3>The answer</h3>
              <p>
                <strong>Never.</strong> Being handed the solution is the one
                thing that reliably teaches you nothing.
              </p>
            </div>
          </li>
        </ol>
      </section>

      <section className="band" aria-labelledby="features-heading">
        <h2 id="features-heading">What you get</h2>
        <div className="grid-2">
          {FEATURES.map((feature) => (
            <article key={feature.title} className="card feature">
              <span className="feature-icon" aria-hidden>
                {feature.icon}
              </span>
              <h3>{feature.title}</h3>
              <p>{feature.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="band cta-band">
        <h2>Ready to break something?</h2>
        <Link
          className="btn btn-primary btn-lg"
          to={signedIn ? '/exercises' : '/signup'}
        >
          {signedIn ? 'Keep going' : 'Start free'}
        </Link>
        <p className="muted small">Takes about a minute to get running.</p>
      </section>

      <footer className="landing-footer">
        <span className="wordmark">
          <span className="mark" aria-hidden>
            {'{ }'}
          </span>
          CodeJourney
        </span>
        <span className="muted small">A CS4530 project</span>
      </footer>
    </div>
  )
}
