import { useState } from 'react'

import { highlightPython } from '../Markdown'
import { firstListLiteral, isRunnable } from '../../lib/lessonBlocks'
import { runSnippet } from '../../lib/runner'

/**
 * A code example in a lesson.
 *
 * Everything here exists to stop a snippet being a grey rectangle you skim:
 *
 *   run       Pyodide is already in this bundle, so an example can simply be
 *             executed. Reading that `quests[0]` is "Slay the dragon" is worth
 *             less than watching it happen.
 *   output    printed results get their own terminal panel rather than hiding
 *             in a comment, so the block reads as a session.
 *   diagram   a plain list literal is drawn as boxes with their indices, which
 *             is the one thing every beginner gets wrong and the one thing a
 *             sentence explains badly.
 *   pins      `# (1)` markers in the source pair with the notes underneath.
 *   copy      because people will want to paste it into the editor.
 *
 * A snippet is only offered as runnable when it plausibly does something on its
 * own. A fragment with a bare `return` in it is an illustration, not a program,
 * and offering to run it would produce a syntax error that teaches nothing.
 */

export function CodeBlock({
  code,
  lang,
  annotations,
  notes,
  prelude = '',
}: {
  code: string
  lang: string
  annotations: string[]
  /** The ordered list that followed, if this block had `# (n)` pins. */
  notes?: string[]
  /** Earlier runnable blocks in the lesson, replayed silently before this one. */
  prelude?: string
}) {
  const [copied, setCopied] = useState(false)
  const [busy, setBusy] = useState(false)
  const [output, setOutput] = useState<{ stdout: string; error: string | null } | null>(
    null
  )

  const python = lang === 'python' || lang === 'py'
  const diagram = python ? firstListLiteral(code) : null
  const canRun = python && isRunnable(code)

  async function run() {
    setBusy(true)
    setOutput(null)
    try {
      setOutput(await runSnippet(code, prelude))
    } finally {
      setBusy(false)
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      /* Clipboard refused (permissions, insecure context). Not worth a message. */
    }
  }

  return (
    <figure className="cb">
      <div className="cb-bar">
        <span className="cb-lights" aria-hidden>
          <i /> <i /> <i />
        </span>
        <span className="cb-lang">{python ? 'python' : lang || 'text'}</span>
        <span className="cb-actions">
          {canRun && (
            <button type="button" onClick={run} disabled={busy} className="cb-run">
              {busy ? 'Running…' : '▶ Run'}
            </button>
          )}
          <button type="button" onClick={copy} className="cb-copy">
            {copied ? 'Copied' : 'Copy'}
          </button>
        </span>
      </div>

      <pre className="cb-code">
        <code>{python ? highlightPython(code) : code}</code>
      </pre>

      {annotations.length > 0 && notes && notes.length > 0 && (
        <ol className="cb-notes">
          {notes.map((note, i) => (
            <li key={i}>{note}</li>
          ))}
        </ol>
      )}

      {output && (
        <div className={output.error ? 'cb-out cb-out-err' : 'cb-out'}>
          <span className="cb-out-label">
            {output.error ? 'Error' : 'Output'}
          </span>
          <pre>{output.error ?? output.stdout.trimEnd() ?? ''}</pre>
          {!output.error && !output.stdout.trim() && (
            <p className="muted small">
              It ran, and printed nothing — this example defines things rather
              than showing them. Add a <code>print(...)</code> to see inside.
            </p>
          )}
        </div>
      )}

      {diagram && (
        <figcaption className="cb-diagram">
          <span className="cb-diagram-name">{diagram.name}</span>
          <span className="cb-cells">
            {diagram.items.map((item, index) => (
              <span key={index} className="cb-cell">
                <span className="cb-cell-value">{item}</span>
                <span className="cb-cell-index">{index}</span>
              </span>
            ))}
          </span>
          <span className="cb-diagram-note">
            positions start at 0, so the last one is{' '}
            {diagram.items.length - 1}
          </span>
        </figcaption>
      )}
    </figure>
  )
}
