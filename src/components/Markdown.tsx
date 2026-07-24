import type { ReactNode } from 'react'

/**
 * A deliberately small Markdown renderer for lesson and exercise text.
 *
 * Covers only what the content actually uses: headings, fenced code, inline
 * code, bold, italics, bullet and numbered lists, and paragraphs.
 *
 * Why not a library: every Markdown package renders to an HTML string, which
 * means `dangerouslySetInnerHTML` and a sanitiser to audit alongside it. This
 * builds React elements directly, so there is no HTML injection path at all --
 * a script tag in lesson text renders as the literal characters. Content is
 * authored by the team today, but the instructor authoring tools in the
 * proposal would make this student-adjacent input, and the safe version costs
 * about eighty lines.
 */

export function Markdown({ source }: { source: string }) {
  return <div className="md">{render(source)}</div>
}

/** For short strings -- quiz prompts, options -- where a block layout would be
 *  wrong but `code` and **bold** still need rendering. */
export function InlineMarkdown({ source }: { source: string }) {
  return <>{inline(source)}</>
}

function render(source: string): ReactNode[] {
  const out: ReactNode[] = []
  const lines = source.split('\n')
  let i = 0
  let key = 0

  while (i < lines.length) {
    const line = lines[i]

    // fenced code block
    if (line.startsWith('```')) {
      const body: string[] = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        body.push(lines[i])
        i++
      }
      i++ // closing fence
      out.push(
        <pre key={key++} className="md-code">
          <code>{body.join('\n')}</code>
        </pre>
      )
      continue
    }

    // headings
    const heading = /^(#{1,4})\s+(.*)$/.exec(line)
    if (heading) {
      const depth = heading[1].length
      const text = inline(heading[2])
      // Lesson bodies start at ## so they sit under the page's h1. Shift down
      // one level so the document outline stays valid for screen readers.
      out.push(
        depth <= 2 ? (
          <h3 key={key++}>{text}</h3>
        ) : (
          <h4 key={key++}>{text}</h4>
        )
      )
      i++
      continue
    }

    // lists -- consecutive bullet or numbered lines become one list
    if (/^\s*[-*]\s+/.test(line) || /^\s*\d+\.\s+/.test(line)) {
      const ordered = /^\s*\d+\.\s+/.test(line)
      const items: ReactNode[] = []
      while (
        i < lines.length &&
        (/^\s*[-*]\s+/.test(lines[i]) || /^\s*\d+\.\s+/.test(lines[i]))
      ) {
        items.push(
          <li key={items.length}>
            {inline(lines[i].replace(/^\s*(?:[-*]|\d+\.)\s+/, ''))}
          </li>
        )
        i++
      }
      out.push(
        ordered ? <ol key={key++}>{items}</ol> : <ul key={key++}>{items}</ul>
      )
      continue
    }

    // blank
    if (line.trim() === '') {
      i++
      continue
    }

    // paragraph -- consume until a blank line or a block starts
    const para: string[] = []
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].startsWith('```') &&
      !/^#{1,4}\s/.test(lines[i]) &&
      !/^\s*[-*]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i])
    ) {
      para.push(lines[i])
      i++
    }
    out.push(<p key={key++}>{inline(para.join(' '))}</p>)
  }

  return out
}

/** Inline spans: `code`, **bold**, *italic*. Order matters -- code first, so
 *  asterisks inside a code span are left alone. */
function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = []
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g
  let last = 0
  let match: RegExpExecArray | null
  let key = 0

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    const token = match[0]
    if (token.startsWith('`')) {
      parts.push(<code key={key++}>{token.slice(1, -1)}</code>)
    } else if (token.startsWith('**')) {
      parts.push(<strong key={key++}>{token.slice(2, -2)}</strong>)
    } else {
      parts.push(<em key={key++}>{token.slice(1, -1)}</em>)
    }
    last = match.index + token.length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}
