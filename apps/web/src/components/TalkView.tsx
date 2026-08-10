import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { AskTeacher } from './AskTeacher'
import { JoinClass } from './JoinClass'
import { Tutor } from './Tutor'
import { api } from '../lib/api'
import type { Dashboard, MyClass } from '../lib/types'

/**
 * Somewhere to ask, without being inside a lesson.
 *
 * Both ways of getting help already existed and both were buried at the bottom
 * of the Reflect stage, which you only reach by finishing an exercise. That is
 * exactly backwards: the moment you most want to ask something is when you are
 * stuck, or between sessions, or before you have started at all.
 *
 * Two people, one switch:
 *
 *   Your coach     answers now, about the lesson you are on
 *   Your teacher   answers later, about anything
 *
 * The difference is stated rather than implied, because they are genuinely
 * different offers and picking the wrong one wastes your time -- a machine
 * cannot tell you the deadline moved, and a person will not reply in four
 * seconds.
 *
 * Joining a class lives here too. Asking a teacher needs one, and sending
 * someone to their account page to find a form, then back here, is three
 * navigations to answer a question they have already typed.
 */

type Who = 'coach' | 'teacher'

export function TalkView({ data }: { data: Dashboard }) {
  const [who, setWho] = useState<Who>('coach')
  const [classes, setClasses] = useState<MyClass[] | null>(null)

  const loadClasses = useCallback(() => {
    api
      .myClasses()
      .then(setClasses)
      // An empty list and a failed lookup lead to the same screen -- the join
      // form -- so there is nothing worth interrupting anyone with.
      .catch(() => setClasses([]))
  }, [])

  useEffect(() => {
    loadClasses()
  }, [loadClasses])

  // The coach talks about a lesson, so it needs one. The lesson you are part
  // way through is the one you are most likely to be asking about; failing
  // that, the one you would open next.
  const lesson =
    data.exercises.find((e) => e.slug === data.continue_slug) ??
    data.exercises.find((e) => e.status === 'in_progress') ??
    data.exercises[0]

  const inAClass = (classes?.length ?? 0) > 0

  return (
    <div className="subview">
      <h1>Ask for help</h1>
      <p className="muted">
        Two people you can ask, and they are good at different things.
      </p>

      <nav className="rtabs talk-tabs" role="tablist" aria-label="Who to ask">
        <button
          type="button"
          role="tab"
          aria-selected={who === 'coach'}
          className={who === 'coach' ? 'rtab is-on' : 'rtab'}
          onClick={() => setWho('coach')}
        >
          <strong>Your coach</strong>
          <span className="rtab-who">Answers now · knows your code</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={who === 'teacher'}
          className={who === 'teacher' ? 'rtab is-on' : 'rtab'}
          onClick={() => setWho('teacher')}
        >
          <strong>Your teacher</strong>
          <span className="rtab-who">
            {inAClass ? 'Answers later · a real person' : 'Needs a class first'}
          </span>
        </button>
      </nav>

      {who === 'coach' ? (
        lesson ? (
          <>
            <p className="talk-context muted small">
              Talking about <strong>{lesson.title}</strong> — the lesson
              you&rsquo;re on.{' '}
              <Link to={`/exercise/${lesson.slug}`}>Open it</Link>
            </p>
            {/* Keyed on the lesson so switching context starts the right saved
                conversation rather than showing the previous lesson's. */}
            <Tutor key={lesson.id} exerciseId={lesson.id} solved={false} />
          </>
        ) : (
          <p className="panel muted">
            Your coach talks about a lesson you&rsquo;re working on. Start one
            and it&rsquo;ll have something to go on.
          </p>
        )
      ) : (
        <>
          {/* The join form comes first while there is no class, because until
              there is one the ask box below it has nobody to send to. */}
          {classes !== null && !inAClass && (
            <div className="talk-join">
              <p className="talk-context muted small">
                Your teacher can see how you&rsquo;re getting on and answer
                questions like this one. Join with the code they gave you.
              </p>
              <JoinClass onChanged={loadClasses} />
            </div>
          )}
          {/* Only once there is somebody to send to. AskTeacher's own empty
              state tells you to go to your account page and join a class --
              true everywhere else, and absurd directly beneath the join form.
              Keyed on membership so joining swaps it in at once: it asks the
              server whether anyone is listening only on mount. */}
          {inAClass && (
            <>
              <AskTeacher key="joined" showHeading={false} />
              <JoinClass onChanged={loadClasses} />
            </>
          )}
        </>
      )}
    </div>
  )
}
