import { Empty, Rule, StruggleBar, ago } from './parts'
import type { TeacherHome } from '../../lib/types'

/**
 * The landing view: what needs you today.
 *
 * Ordered by what a teacher does with it, not by what is easiest to compute.
 * Questions first, because a student who asked is a student waiting on a
 * person. Then the people the platform flagged. Then what the class as a whole
 * found hard, which is next lesson's problem rather than this minute's.
 *
 * Deliberately no roster table here. That is the Students view; putting thirty
 * rows above the three people who need something is how the three get missed.
 */
export function OverviewView({
  data,
  onOpenStudent,
  onGoto,
}: {
  data: TeacherHome
  onOpenStudent: (userId: string) => void
  onGoto: (view: 'students' | 'difficulty' | 'questions' | 'classes') => void
}) {
  const flagged = data.students.filter((s) => s.needs_help)
  const asked = data.students.filter((s) => s.open_questions > 0)
  const quiet = data.students.filter(
    (s) => !s.needs_help && !s.open_questions && s.attempts === 0
  )

  return (
    <div className="tview">
      <div className="tstats">
        <div>
          <dt>Students</dt>
          <dd>{data.total_students}</dd>
        </div>
        <button
          type="button"
          className={data.open_questions ? 'tstat-live' : undefined}
          onClick={() => onGoto('questions')}
        >
          <dt>Questions waiting</dt>
          <dd>{data.open_questions}</dd>
        </button>
        <button
          type="button"
          className={data.needs_help ? 'tstat-flag' : undefined}
          onClick={() => onGoto('students')}
        >
          <dt>Out of hints</dt>
          <dd>{data.needs_help}</dd>
        </button>
        <div>
          <dt>Not started</dt>
          <dd>{quiet.length}</dd>
        </div>
      </div>

      {asked.length > 0 && (
        <section className="tcard">
          <header className="tcard-head">
            <h2>Someone asked you something</h2>
            <button type="button" className="linkish" onClick={() => onGoto('questions')}>
              Open the questions &rarr;
            </button>
          </header>
          <ul className="tpeople">
            {asked.map((s) => (
              <li key={s.user_id}>
                <button type="button" onClick={() => onOpenStudent(s.user_id)}>
                  <span className="tperson-name">{s.display_name}</span>
                  <span className="muted small">
                    {s.open_questions === 1
                      ? '1 question'
                      : `${s.open_questions} questions`}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="tcard">
        <header className="tcard-head">
          <h2>Out of hints and still stuck</h2>
        </header>
        <Rule>
          The platform gives four levels of hint before it runs out. These
          students reached the last one and still haven&rsquo;t solved it &mdash;
          there is nothing left for it to offer them.
        </Rule>
        {flagged.length === 0 ? (
          <p className="muted small">Nobody, right now.</p>
        ) : (
          <ul className="tpeople">
            {flagged.map((s) => (
              <li key={s.user_id}>
                <button type="button" onClick={() => onOpenStudent(s.user_id)}>
                  <span className="tperson-name">{s.display_name}</span>
                  {/* The useful half: which lesson. "Priya needs help" makes
                      the teacher go and find out; this doesn't. */}
                  <span className="muted small">
                    stuck on {s.stuck_on} &middot; last seen {ago(s.last_active_at)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="tcard">
        <header className="tcard-head">
          <h2>Hardest so far</h2>
          <button type="button" className="linkish" onClick={() => onGoto('difficulty')}>
            All of it &rarr;
          </button>
        </header>
        {data.hardest.length === 0 ? (
          <p className="muted small">
            Nothing to measure yet &mdash; this fills in once your class starts
            submitting work.
          </p>
        ) : (
          <ul className="tdiff">
            {data.hardest.slice(0, 5).map((stat) => (
              <li key={stat.key}>
                <span className="tdiff-label">{stat.label}</span>
                <StruggleBar stat={stat} />
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Before anyone has joined, the code IS the dashboard. A teacher who
          has just signed up already has a class and a code -- generated for
          them, so there was no form in the way -- and the useful thing to put
          in front of them is the six characters they are about to read out,
          not a link to the tab holding them. */}
      {data.total_students === 0 && data.classrooms.length > 0 && (
        <section className="tcard tfirst">
          <h2>Read this out to your class</h2>
          <p className="tcode tcode-lg">{data.classrooms[0].join_code}</p>
          <p className="muted small">
            They enter it once, on their account page, and appear here. Nothing
            else on this page fills in until somebody does.
          </p>
          <button type="button" className="linkish" onClick={() => onGoto('classes')}>
            Change the code or add another class &rarr;
          </button>
        </section>
      )}

      {data.total_students === 0 && data.classrooms.length === 0 && (
        <Empty title="No class yet">
          <p className="muted">Make one under Classes to get a code.</p>
        </Empty>
      )}
    </div>
  )
}
