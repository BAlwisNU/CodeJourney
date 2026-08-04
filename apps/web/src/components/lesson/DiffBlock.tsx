import { useState } from 'react'

import { highlightPython } from '../Markdown'
import { parseDiff } from '../../lib/lessonBlocks'

/**
 * The wrong version beside the right one.
 *
 * Written as an ordinary ```diff fence, so the convention is one every
 * programmer already knows and nothing new had to be invented:
 *
 *   - if due_day < today:
 *   + if due_day <= today:
 *
 * A near-miss is the thing worth showing here. Prose describing the difference
 * between `<` and `<=` is easy to nod along to; two lines that differ by one
 * character, one red and one green, is the actual lesson.
 *
 * Copy takes the corrected version -- the `+` and context lines with their
 * markers stripped -- because nobody wants to paste the bug.
 */
export function DiffBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false)
  const lines = parseDiff(code)

  const removed = lines.filter((l) => l.sign === '-').length
  const added = lines.filter((l) => l.sign === '+').length

  async function copy() {
    const fixed = lines
      .filter((line) => line.sign !== '-')
      .map((line) => line.text)
      .join('\n')
    try {
      await navigator.clipboard.writeText(fixed)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      /* Clipboard refused (permissions, insecure context). Not worth a message. */
    }
  }

  return (
    <figure className="cb cb-diff">
      <div className="cb-bar">
        <span className="cb-lights" aria-hidden>
          <i /> <i /> <i />
        </span>
        <span className="cb-lang">before → after</span>
        <span className="cb-actions">
          <span className="cb-diffstat" aria-hidden>
            <b className="minus">−{removed}</b> <b className="plus">+{added}</b>
          </span>
          <button type="button" onClick={copy} className="cb-copy">
            {copied ? 'Copied' : 'Copy the fix'}
          </button>
        </span>
      </div>

      <pre className="cb-code">
        <code>
          {lines.map((line, i) => (
            <span key={i} className={`dl dl-${line.kind}`}>
              <span className="dl-sign" aria-hidden>
                {line.sign === ' ' ? '' : line.sign}
              </span>
              {/* Screen readers get the word, not a punctuation mark that
                  reads as nothing or as a minus sign. */}
              {line.sign !== ' ' && (
                <span className="sr-only">
                  {line.sign === '-' ? 'before: ' : 'after: '}
                </span>
              )}
              {/* No trailing newline: the row is display:block, so a `\n`
                  inside a <pre> would add a second, empty line box. */}
              <span className="dl-text">{highlightPython(line.text)}</span>
            </span>
          ))}
        </code>
      </pre>
    </figure>
  )
}
