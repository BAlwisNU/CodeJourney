import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ErrorDemo } from '../components/ErrorDemo'
import { HeroDeck } from '../components/HeroDeck'
import { Icon, type IconName } from '../components/Icon'
import { ScrollWorld } from '../components/ScrollWorld'
import { Tilt } from '../components/Tilt'
import { TopicExplorer } from '../components/TopicExplorer'
import { api, token } from '../lib/api'
import { useRevealOnScroll } from '../lib/motion'

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

// Languages, not topics-within-Python -- the marketing mirrors the app's own
// top-level navigation. Only Python is live; the rest are honestly "soon",
// because each needs its own executor, not just its own lessons.
const LANGUAGES = [
  {
    key: 'python',
    short: 'Py',
    name: 'Python',
    shape: 'Available now',
    example: 'The best first language. Runs right in your browser.',
    soon: false,
  },
  {
    key: 'cpp',
    short: 'C++',
    name: 'C++',
    shape: 'Coming soon',
    example: 'Speed and control, closer to the machine.',
    soon: true,
  },
  {
    key: 'html',
    short: '</>',
    name: 'HTML & CSS',
    shape: 'Coming soon',
    example: 'Build things you can see, in the browser.',
    soon: true,
  },
  {
    key: 'sql',
    short: 'SQL',
    name: 'SQL',
    shape: 'Coming soon',
    example: 'Ask questions of data and get answers back.',
    soon: true,
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

const HERO_STATS = [
  { value: '0', label: 'things to install' },
  { value: '∞', label: 'tries per exercise' },
  { value: '5', label: 'levels of help' },
  { value: '0', label: 'times we show the answer' },
]

const FEATURES = [
  { icon: 'bolt' as IconName, title: 'Runs as you type', body: 'Python runs inside the browser tab. Press Run and it answers immediately — nothing to install, nothing to wait for.' },
  { icon: 'reorder' as IconName, title: 'Warm up first', body: 'Drag jumbled lines into the right order before facing an empty editor. Two of them don’t belong — spotting that is the puzzle.' },
  { icon: 'watch' as IconName, title: 'Watch it run', body: 'Step through your program line by line and see exactly what each one does to your data.' },
  { icon: 'journal' as IconName, title: 'Keep the receipts', body: 'What you tried, where you got stuck, how you fixed it — building a portfolio that shows how far you came, not just your final answers.' },
]

export function LandingPage() {
  const navigate = useNavigate()
  const signedIn = Boolean(token.get())
  const [openWorld, setOpenWorld] = useState<string | null>('python')
  const [demoBusy, setDemoBusy] = useState<'lesson' | 'account' | null>(null)
  const [demoError, setDemoError] = useState<string | null>(null)

  useRevealOnScroll()

  /**
   * Try it without signing up.
   *
   * Both buttons mint a throwaway account server-side and then go somewhere
   * worth looking at: straight into a real exercise, or into a dashboard that
   * already has a few days of work in it. A demo of an empty dashboard shows
   * nothing about what the product is for.
   */
  async function startDemo(kind: 'lesson' | 'account') {
    if (demoBusy) return
    setDemoBusy(kind)
    setDemoError(null)
    try {
      const { access_token } = await api.startDemo(kind === 'account')
      token.set(access_token)
      navigate(kind === 'lesson' ? '/exercise/lists-make' : '/exercises')
    } catch (err) {
      setDemoError(err instanceof Error ? err.message : String(err))
      setDemoBusy(null)
    }
  }

  return (
    <div className="landing">
      {/* The world the page flies through. Fixed, behind everything, and
          removed entirely under prefers-reduced-motion. */}
      <ScrollWorld />

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
              {/* Try-before-signup, ahead of the account buttons: someone who
                  is not yet convinced should meet the thing itself before they
                  meet a form. */}
              <button
                type="button"
                className="btn btn-ghost btn-demo"
                onClick={() => void startDemo('lesson')}
                disabled={demoBusy !== null}
              >
                {demoBusy === 'lesson' ? 'Opening…' : 'Try a lesson'}
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-demo"
                onClick={() => void startDemo('account')}
                disabled={demoBusy !== null}
              >
                {demoBusy === 'account' ? 'Setting up…' : 'Demo account'}
              </button>
              <span className="nav-divider" aria-hidden />
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

      {demoError && (
        <p className="panel panel-error small demo-error">{demoError}</p>
      )}

      <section className="hero">
        <div className="hero-grid">
          <div className="hero-copy">
            <h1>
              Write real code.<br />
              Break it. <span className="grad">Find out why.</span>
            </h1>
            <p className="lede">
              Most people quit programming for the same two reasons: the
              exercises are dull, and when the code breaks all you get is red
              text and the word <em>wrong</em>. CodeJourney fixes both — you
              build things worth building, and every failure comes with an
              explanation.
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
          </div>

          {/* The pitch, as an object: code, the traceback, the translation --
              stacked in depth and leaning toward wherever you point. */}
          <HeroDeck />
        </div>

        <ul className="hero-stats">
          {HERO_STATS.map((stat) => (
            <Tilt as="li" key={stat.label} max={9} lift={10}>
              <strong>{stat.value}</strong>
              <span>{stat.label}</span>
            </Tilt>
          ))}
        </ul>

        <p className="scroll-cue" aria-hidden>
          <span className="scroll-cue-rail">
            <span className="scroll-cue-dot" />
          </span>
          Scroll to fly through
        </p>
      </section>

      {/* The proof, and the most persuasive thing on the page: press a button,
          watch a traceback become a sentence. */}
      <section className="band" aria-labelledby="demo-heading">
        <h2 id="demo-heading" data-reveal>Try breaking something</h2>
        <p className="section-lede" data-reveal>
          Pick a mistake everyone makes in their first week, and press Run. This
          is the real translation, word for word.
        </p>
        <div data-reveal>
          <ErrorDemo />
        </div>
      </section>

      <section className="band" aria-labelledby="worlds-heading">
        <h2 id="worlds-heading" data-reveal>Start with Python. More on the way.</h2>
        <p className="section-lede" data-reveal>
          Python first, because it&rsquo;s the kindest place to begin. C++, HTML
          &amp; CSS, and SQL are next — same layered feedback, same explain-it
          -when-it-breaks approach.
        </p>

        <ul className="worlds">
          {LANGUAGES.map((lang) => (
            <li
              key={lang.key}
              className={openWorld === lang.key ? 'world on' : 'world'}
              data-reveal
            >
              <button
                type="button"
                onClick={() =>
                  setOpenWorld(openWorld === lang.key ? null : lang.key)
                }
                aria-expanded={openWorld === lang.key}
              >
                <span className="lang-chip" aria-hidden>
                  {lang.short}
                </span>
                <span className="world-name">{lang.name}</span>
                <span className={lang.soon ? 'world-shape soon' : 'world-shape'}>
                  {lang.shape}
                </span>
              </button>
              {openWorld === lang.key && (
                <div className="world-panel">
                  <p className="world-example">{lang.example}</p>
                  {/* Only the live language has a curriculum to show. The
                      others get their one-line "coming soon" and nothing
                      more, which is the honest shape of what exists. */}
                  {!lang.soon && <TopicExplorer />}
                </div>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="band" aria-labelledby="ladder-heading">
        <h2 id="ladder-heading" data-reveal>Stuck? Help arrives in steps</h2>
        <p className="section-lede" data-reveal>
          Each rung tells you a little more. Retrying costs you nothing, and the
          last step is a human being — never the answer.
        </p>

        <ol className="ladder">
          {LADDER.map((step) => (
            <li key={step.tag} data-reveal>
              <span className="rung">{step.tag}</span>
              <div className="rung-body">
                <h3>
                  {step.title} <span className="when">{step.when}</span>
                </h3>
                <p>{step.body}</p>
              </div>
            </li>
          ))}
          <li className="never" data-reveal>
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
        <h2 id="features-heading" data-reveal>What you get</h2>
        <div className="grid-2">
          {FEATURES.map((feature) => (
            <Tilt key={feature.title} className="feature-tilt" max={6} lift={16}>
              <article className="card feature" data-reveal>
                <span className="feature-icon" aria-hidden>
                  <Icon name={feature.icon} size={26} />
                </span>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
              </article>
            </Tilt>
          ))}
        </div>
      </section>

      <section className="band cta-band" data-reveal>
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
