import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ErrorDemo } from '../components/ErrorDemo'
import { AgentTabs } from '../components/AgentTabs'
import { PlanetScroll } from '../components/PlanetScroll'
import { HeroDeck } from '../components/HeroDeck'
import { Icon, type IconName } from '../components/Icon'
import { ScrollWorld } from '../components/ScrollWorld'
import { Tilt } from '../components/Tilt'
import { TopicExplorer } from '../components/TopicExplorer'
import { api, token } from '../lib/api'
import { demoMarker, endDemo } from '../lib/demo'
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

// Three of these are about how the platform teaches; the fourth is about how
// much there is to teach, which is the question "is this a real thing or a
// demo?" that the other three cannot answer. Pinned to the actual library size
// by a test -- a landing page that overstates the content is worse than one
// that says nothing about it.
const HERO_STATS = [
  { value: '0', label: 'things to install' },
  { value: '∞', label: 'tries per exercise' },
  { value: '5', label: 'levels of help' },
  { value: '69', label: 'exercises to work through' },
]

const FEATURES = [
  { icon: 'bolt' as IconName, title: 'Runs as you type', body: 'Python runs in the tab. Press Run, get an answer. Nothing to install.' },
  { icon: 'reorder' as IconName, title: 'Warm up first', body: 'Order the jumbled lines before facing an empty editor. Two don’t belong.' },
  { icon: 'watch' as IconName, title: 'Watch it run', body: 'Step through your program and watch what each line does to your data.' },
  { icon: 'journal' as IconName, title: 'Keep the receipts', body: 'What you tried, where you got stuck, how you fixed it. The journey, not just the answers.' },
]

export function LandingPage() {
  const navigate = useNavigate()

  // Reaching the front door ends a lesson demo, however you got here -- the
  // exit tab, the back button, or typing the address. Done before the first
  // render rather than in an effect, so the nav never briefly offers "Keep
  // going" for an account that is about to be discarded.
  if (token.get() && demoMarker.get() === 'lesson') endDemo()

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
      // After token.set, which clears any previous marker.
      demoMarker.set(kind)
      // The lesson demo starts at Plan, which is step 1 of its flow -- the
      // lesson, the quiz and the warm-up come before an empty editor. Dropping
      // someone straight into the editor skips the part that explains what
      // they are about to write.
      navigate(kind === 'lesson' ? '/exercise/lists-make/plan' : '/exercises')
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

      {/* Frosted glass between the world and the page. Sits directly after the
          canvas at the same z-index, so it paints over the world and under
          every section, all of which are position:relative z-index:1. Fixed
          and full height, so the column stays frosted the whole way down
          rather than only behind the hero. */}
      <div className="landing-glass" aria-hidden />

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
                {demoBusy === 'lesson' ? 'Opening…' : 'Demo Lesson'}
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

      <PlanetScroll
        slides={[
      <section className="hero" key="hero">
        <div className="hero-grid">
          <div className="hero-copy">
            <h1>
              Write real code.<br />
              Break it. <span className="grad">Find out why.</span>
            </h1>
            <p className="lede">
              Build things worth building. When it breaks, you get an
              explanation — not the word <em>wrong</em>.
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
      </section>,

      /* The proof, and the most persuasive thing on the page: press a button,
          watch a traceback become a sentence. */
      <section className="band" aria-labelledby="demo-heading" key="demo">
        <h2 id="demo-heading" data-reveal>Try breaking something</h2>
        <p className="section-lede" data-reveal>
          Press Run. That is the real translation.
        </p>
        <div data-reveal>
          <ErrorDemo />
        </div>
      </section>,

      <section className="band" aria-labelledby="worlds-heading" key="worlds">
        <h2 id="worlds-heading" data-reveal>Start with Python. More on the way.</h2>
        <p className="section-lede" data-reveal>
          C++, HTML &amp; CSS and SQL are next.
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
                  {/* Compact: on the landing page this is proof that a real
                      curriculum exists, not the curriculum itself. Every
                      module's one-line blurb was 339 words of the page. The
                      dashboard shows the full version, where somebody is
                      choosing what to do next rather than deciding whether to
                      sign up. */}
                  {!lang.soon && <TopicExplorer compact />}
                </div>
              )}
            </li>
          ))}
        </ul>
      </section>,

      <section className="band" aria-labelledby="ladder-heading" key="ladder">
        <h2 id="ladder-heading" data-reveal>Stuck? Help arrives in steps</h2>
        <p className="section-lede" data-reveal>
          Each rung says a little more. The last one is a person.
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
      </section>,

      <section className="band" aria-labelledby="agents-heading" key="agents">
        <h2 id="agents-heading" data-reveal>
          Your personalised coach and best friend in your coding journey
        </h2>
        {/* The heading now carries "on your side", so the lede drops the line
            that said it twice and spends itself on what makes that credible:
            it has actually read the thing you are working on. */}
        <p className="section-lede" data-reveal>
          It has read your lesson and your code, and knows what you came to build.
        </p>

        <AgentTabs />

        {/* The boundary is the most important thing on this page, so it is
            stated rather than implied. It is enforced structurally and pinned
            by test_tutor_never_receives_the_private_journal. */}
        <p className="agent-rule" data-reveal>
          <strong>And one thing they never see.</strong> Your journal. The one
          place you can write “I have no idea what I am doing” and know nothing
          is reading it back.
        </p>
      </section>,

      <section className="band" aria-labelledby="features-heading" key="features">
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
      </section>,

      <section className="band cta-band" data-reveal key="cta">
        <h2>Ready to break something?</h2>
        <Link
          className="btn btn-primary btn-lg"
          to={signedIn ? '/exercises' : '/signup'}
        >
          {signedIn ? 'Keep going' : 'Start free'}
        </Link>
        <p className="muted small">Takes about a minute to get running.</p>
      </section>,
        ]}
      />

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
