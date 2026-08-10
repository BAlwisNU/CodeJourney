import { useState, type ReactNode } from 'react'

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

/**
 * A fenced code block, with a way to take the code with you.
 *
 * The lessons' own blocks have had Run and Copy since they were written; code
 * the coach types in a chat bubble had neither, so the one place a student is
 * handed a worked example in response to their own question was the one place
 * they had to retype it or select it by hand.
 *
 * Copy only, not Run: this renders inside chat bubbles and prose alike, and a
 * Run button needs an exercise and a harness around it. Copy is the action
 * that always makes sense.
 */
function CodeBlockWithCopy({
  code,
  lang,
  python,
}: {
  code: string
  lang?: string
  python: boolean
}) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      // Clipboard permission can be refused and the code is on screen anyway --
      // nothing to recover from, and nothing worth interrupting for.
    }
  }

  return (
    <div className="md-code-wrap">
      <pre className="md-code" data-lang={lang}>
        <code>{python ? highlightPython(code) : code}</code>
      </pre>
      <button type="button" className="md-copy" onClick={() => void copy()}>
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  )
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
      const lang = line.slice(3).trim().toLowerCase()
      const body: string[] = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        body.push(lines[i])
        i++
      }
      i++ // closing fence
      const code = body.join('\n')
      const python = lang === 'python' || lang === 'py'
      out.push(
        <CodeBlockWithCopy
          key={key++}
          code={code}
          lang={python ? 'python' : lang || undefined}
          python={python}
        />
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

/**
 * Colour Python source, without a highlighting library.
 *
 * Lessons are mostly code, and unlit monospace is the difference between a
 * snippet you read and one you skim past. The comments matter most: this
 * content uses them to show what an expression evaluates to
 * (`quests[0]        # "Slay the dragon"`), so a distinct colour turns a wall
 * of grey into example-and-answer.
 *
 * Same reasoning as the renderer above -- this returns React elements, so
 * highlighting can never introduce an HTML injection path. A library here would
 * be ~40kB and a `dangerouslySetInnerHTML` to audit, for one language.
 *
 * One regex, alternation ordered by precedence: comments and strings win over
 * everything, so a `#` inside a string and a keyword inside a comment are both
 * left alone.
 */
const PY_TOKENS = new RegExp(
  [
    '(#[^\\n]*)', // comment
    '("""[\\s\\S]*?"""|\'\'\'[\\s\\S]*?\'\'\'|"(?:\\\\.|[^"\\\\])*"|\'(?:\\\\.|[^\'\\\\])*\')', // string
    '\\b(\\d+\\.?\\d*)\\b', // number
    '\\b(False|None|True|and|as|assert|break|class|continue|def|del|elif|else|' +
      'except|finally|for|from|global|if|import|in|is|lambda|not|or|pass|raise|' +
      'return|try|while|with|yield)\\b', // keyword
    '\\b(abs|all|any|bool|dict|enumerate|float|input|int|len|list|max|min|open|' +
      'print|range|reversed|round|set|sorted|str|sum|tuple|zip|append|split|join|' +
      'strip|items|keys|values|get)\\b', // builtin / common method
  ].join('|'),
  'g'
)

const TOKEN_CLASS = ['tok-comment', 'tok-str', 'tok-num', 'tok-kw', 'tok-fn']

export function highlightPython(code: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  let key = 0
  let match: RegExpExecArray | null

  PY_TOKENS.lastIndex = 0
  while ((match = PY_TOKENS.exec(code)) !== null) {
    if (match.index > last) out.push(code.slice(last, match.index))
    // Which alternative matched decides the colour.
    const group = match.slice(1).findIndex((g) => g !== undefined)
    out.push(
      <span key={key++} className={TOKEN_CLASS[group] ?? ''}>
        {match[0]}
      </span>
    )
    last = match.index + match[0].length
  }
  if (last < code.length) out.push(code.slice(last))
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
