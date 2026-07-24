import { useState } from 'react'

/**
 * The landing page's interactive proof.
 *
 * Pick a broken snippet, press Run, watch the raw traceback turn into a
 * sentence. Every translation here is the literal output of the real rule table
 * in apps/api/app/services/translate.py -- copied, not invented. If a rule
 * changes, this should change with it, because a demo that promises something
 * the product doesn't do is worse than no demo.
 *
 * Not wired to a live interpreter on purpose: Pyodide is a ~10MB WASM download,
 * and making the first-impression page slow to prove that the product is fast
 * would be a poor trade. The editor loads it; the shop window doesn't.
 */

type Sample = {
  label: string
  code: string
  traceback: string
  translated: string
  line: number
}

const SAMPLES: Sample[] = [
  {
    label: 'A typo',
    code: `quests = ["Slay the dragon"]\nprint(qwests)`,
    traceback: `Traceback (most recent call last):
  File "main.py", line 2, in <module>
    print(qwests)
          ^^^^^^
NameError: name 'qwests' is not defined`,
    translated:
      'You’ve used the name “qwests”, but Python hasn’t seen it before. Either it’s spelled differently from where you created it, or it hasn’t been created yet.',
    line: 2,
  },
  {
    label: 'Off the end',
    code: `quests = ["Slay the dragon", "Find the sword"]\nprint(quests[5])`,
    traceback: `Traceback (most recent call last):
  File "main.py", line 2, in <module>
    print(quests[5])
          ~~~~~~^^^
IndexError: list index out of range`,
    translated:
      'You asked for an item at a position that doesn’t exist — the list is shorter than that. Remember the first item is at 0, so a list of 3 items has positions 0, 1 and 2.',
    line: 2,
  },
  {
    label: 'A loop that never ends',
    code: `hp = 10\nwhile hp > 0:\n    print("still fighting")`,
    traceback: `(no output — the program was stopped after 5 seconds)`,
    translated:
      'Your program was still running after 5 seconds, so it was stopped. That almost always means a loop whose condition never becomes false.',
    line: 2,
  },
  {
    label: 'Adding text to a number',
    code: `score = 42\nprint("Score: " + score)`,
    traceback: `Traceback (most recent call last):
  File "main.py", line 2, in <module>
    print("Score: " + score)
          ~~~~~~~~~~^~~~~~~
TypeError: can only concatenate str (not "int") to str`,
    translated:
      'You’re adding text to something that isn’t text. Python won’t guess what you meant — turn the other value into text first, with str().',
    line: 2,
  },
]

export function ErrorDemo() {
  const [index, setIndex] = useState(0)
  const [state, setState] = useState<'idle' | 'running' | 'done'>('idle')
  const sample = SAMPLES[index]

  function pick(next: number) {
    setIndex(next)
    setState('idle')
  }

  function run() {
    setState('running')
    // A beat of latency so the reveal reads as a result rather than a toggle.
    setTimeout(() => setState('done'), 550)
  }

  return (
    <div className="demo">
      <div className="demo-tabs" role="tablist" aria-label="Example mistakes">
        {SAMPLES.map((s, i) => (
          <button
            key={s.label}
            role="tab"
            aria-selected={i === index}
            className={i === index ? 'demo-tab on' : 'demo-tab'}
            onClick={() => pick(i)}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="demo-body">
        <div className="demo-editor">
          <div className="demo-chrome">
            <span className="dotr" /> <span className="doty" /> <span className="dotg" />
            <span className="demo-file">main.py</span>
          </div>
          <pre>
            {sample.code.split('\n').map((line, i) => (
              <div
                key={i}
                className={
                  state === 'done' && i + 1 === sample.line ? 'ln lit' : 'ln'
                }
              >
                <span className="lno">{i + 1}</span>
                {line}
              </div>
            ))}
          </pre>
          <div className="demo-actions">
            <button className="primary" onClick={run} disabled={state === 'running'}>
              {state === 'running' ? 'Running…' : '▶ Run'}
            </button>
          </div>
        </div>

        <div className="demo-out">
          {state === 'idle' && (
            <p className="muted small demo-idle">
              Press <strong>Run</strong> to see what happens when it breaks.
            </p>
          )}

          {state === 'running' && <p className="muted small demo-idle">Running…</p>}

          {state === 'done' && (
            <div className="demo-result">
              <div className="demo-raw">
                <span className="demo-tag bad">What Python says</span>
                <pre>{sample.traceback}</pre>
              </div>
              <div className="demo-good">
                <span className="demo-tag good">What we say</span>
                <p>{sample.translated}</p>
                <p className="demo-where">
                  Look at <strong>line {sample.line}</strong>.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
