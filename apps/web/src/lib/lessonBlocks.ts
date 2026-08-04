/**
 * Markdown, parsed into typed blocks.
 *
 * The renderer in components/Markdown.tsx turns Markdown straight into
 * elements, which is right for a chat reply or an error explanation. A lesson
 * needs more than that -- it groups blocks under headings, runs code, draws
 * diagrams, folds sections away -- and none of that is possible once the source
 * has already become JSX.
 *
 * So the parse and the render are separated here. This file only decides *what*
 * the blocks are; components/lesson/ decides what they look like.
 */

export type Block =
  | { kind: 'heading'; depth: number; text: string }
  | { kind: 'para'; text: string }
  | { kind: 'code'; lang: string; code: string; annotations: string[] }
  | { kind: 'list'; ordered: boolean; items: string[] }
  | { kind: 'callout'; tone: CalloutTone; title: string; body: string[] }

export type CalloutTone = 'idea' | 'watch' | 'try'

/** A section is a heading plus everything under it, so it can fold as a unit. */
export type Section = { heading: string | null; blocks: Block[] }

/**
 * Headings that are really asides.
 *
 * The lesson content already writes them this way -- "One thing to watch" is
 * the last section of the lists lesson -- so recognising the phrasing turns
 * existing content into callouts with no rewriting. Anything unmatched stays an
 * ordinary heading, which is the safe direction to be wrong in.
 */
const CALLOUT_HEADINGS: [RegExp, CalloutTone][] = [
  [/^(one thing to watch|watch out|careful|a common mistake|gotcha)/i, 'watch'],
  [/^(the (big |key )?idea|worth knowing|remember|in short)/i, 'idea'],
  [/^(try (this|it)|your turn|have a go)/i, 'try'],
]

export function calloutToneFor(heading: string): CalloutTone | null {
  for (const [pattern, tone] of CALLOUT_HEADINGS) {
    if (pattern.test(heading.trim())) return tone
  }
  return null
}

/**
 * Trailing `# (1)` markers in code, paired with a following ordered list.
 *
 * Lets a block be annotated without inventing new syntax: the numbers live in
 * the code as ordinary comments, so the snippet still runs, and the notes are
 * just a numbered list underneath.
 */
const ANNOTATION = /\s*#\s*\((\d+)\)\s*$/

export function parseBlocks(source: string): Block[] {
  const out: Block[] = []
  const lines = source.split('\n')
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    if (line.startsWith('```')) {
      const lang = line.slice(3).trim().toLowerCase()
      const body: string[] = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        body.push(lines[i])
        i++
      }
      i++
      // Pull out any "# (n)" markers so the code stays runnable and the numbers
      // can be rendered as pins instead.
      const annotations: string[] = []
      const cleaned = body.map((l) => {
        const match = ANNOTATION.exec(l)
        if (!match) return l
        annotations.push(match[1])
        return l.replace(ANNOTATION, '')
      })
      out.push({
        kind: 'code',
        lang,
        code: cleaned.join('\n'),
        annotations,
      })
      continue
    }

    const heading = /^(#{1,4})\s+(.*)$/.exec(line)
    if (heading) {
      out.push({ kind: 'heading', depth: heading[1].length, text: heading[2] })
      i++
      continue
    }

    // Blockquotes become callouts. `> **Watch out:** ...` sets the tone from
    // its own label; a bare quote is a neutral "idea".
    if (/^\s*>\s?/.test(line)) {
      const body: string[] = []
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
        body.push(lines[i].replace(/^\s*>\s?/, ''))
        i++
      }
      const label = /^\*\*(.+?)\*\*:?\s*/.exec(body[0] ?? '')
      const title = label ? label[1] : 'Worth knowing'
      if (label) body[0] = body[0].slice(label[0].length)
      out.push({
        kind: 'callout',
        tone: calloutToneFor(title) ?? 'idea',
        title,
        body: body.filter((l) => l.trim() !== ''),
      })
      continue
    }

    if (/^\s*[-*]\s+/.test(line) || /^\s*\d+\.\s+/.test(line)) {
      const ordered = /^\s*\d+\.\s+/.test(line)
      const items: string[] = []
      while (
        i < lines.length &&
        (/^\s*[-*]\s+/.test(lines[i]) || /^\s*\d+\.\s+/.test(lines[i]))
      ) {
        items.push(lines[i].replace(/^\s*(?:[-*]|\d+\.)\s+/, ''))
        i++
      }
      out.push({ kind: 'list', ordered, items })
      continue
    }

    if (line.trim() === '') {
      i++
      continue
    }

    const para: string[] = []
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].startsWith('```') &&
      !/^#{1,4}\s/.test(lines[i]) &&
      !/^\s*>\s?/.test(lines[i]) &&
      !/^\s*[-*]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i])
    ) {
      para.push(lines[i])
      i++
    }
    out.push({ kind: 'para', text: para.join(' ') })
  }

  return out
}

/** Group blocks under their headings so each section can fold as a unit. */
export function toSections(blocks: Block[]): Section[] {
  const sections: Section[] = []
  let current: Section = { heading: null, blocks: [] }

  for (const block of blocks) {
    // Only sub-headings start a new section. A depth-1/2 heading is the
    // lesson's own title, already shown above the body.
    if (block.kind === 'heading' && block.depth >= 3) {
      if (current.blocks.length || current.heading) sections.push(current)
      current = { heading: block.text, blocks: [] }
      continue
    }
    if (block.kind === 'heading' && block.depth <= 2) continue
    current.blocks.push(block)
  }
  if (current.blocks.length || current.heading) sections.push(current)
  return sections
}

/**
 * Roughly how long this takes to read.
 *
 * 200 words a minute for prose, and code counted at a third of that -- nobody
 * reads a snippet at reading speed, they stop and work through it. Rounded up,
 * and never shown as zero.
 */
export function readingMinutes(blocks: Block[]): number {
  let words = 0
  for (const block of blocks) {
    if (block.kind === 'para') words += block.text.split(/\s+/).length
    else if (block.kind === 'list') words += block.items.join(' ').split(/\s+/).length
    else if (block.kind === 'callout') words += block.body.join(' ').split(/\s+/).length
    else if (block.kind === 'code') words += block.code.split(/\s+/).length * 3
  }
  return Math.max(1, Math.round(words / 200))
}

/**
 * Whether a snippet is a program rather than a fragment quoted for shape.
 *
 * A bare `return` outside a function, or an elided `...`, means the author is
 * showing a pattern, not something that runs. Offering Run on those produces a
 * syntax error that teaches nothing.
 */
export function isRunnable(code: string): boolean {
  const trimmed = code.trim()
  if (!trimmed) return false
  if (/^\s*return\b/m.test(trimmed) && !/^\s*def\b/m.test(trimmed)) return false
  if (/^\s*\.{3}\s*$/m.test(trimmed)) return false
  return true
}

/**
 * For each code block, everything runnable that came before it in the lesson.
 *
 * A lesson reads as one continuous session: the second snippet loops over a
 * list the first one defined. Running a block on its own therefore raises
 * NameError, which tells the reader only that the button is broken. Replaying
 * the earlier blocks first -- silently, in the same namespace -- makes Run mean
 * what a reader assumes it means.
 *
 * Keyed on the block object itself, which survives being grouped into sections
 * because the grouping reuses the same objects rather than copying them.
 */
export function buildPreludes(blocks: Block[]): Map<Block, string> {
  const preludes = new Map<Block, string>()
  const sofar: string[] = []

  for (const block of blocks) {
    if (block.kind !== 'code') continue
    const python = block.lang === 'python' || block.lang === 'py'
    if (!python) continue
    preludes.set(block, sofar.join('\n'))
    // Only runnable blocks join the prelude; a fragment would break every
    // later block that replayed it.
    if (isRunnable(block.code)) sofar.push(block.code)
  }
  return preludes
}

export type DiffLine = {
  sign: '-' | '+' | ' '
  kind: 'del' | 'add' | 'same'
  text: string
}

/**
 * A ```diff fence, split into before/after/context lines.
 *
 * Deliberately only the line-prefix part of the diff format: no hunk headers,
 * no `@@` ranges, no file names. A lesson is showing two versions of four
 * lines, not the output of `git diff`, and a parser that accepted more would
 * imply the renderer could draw more.
 *
 * A leading space is optional, so a fence can be written without padding every
 * unchanged line -- authors forget, and the alternative is a diff that silently
 * loses its first character.
 */
export function parseDiff(code: string): DiffLine[] {
  return code.split('\n').map((line) => {
    if (line.startsWith('-')) return { sign: '-', kind: 'del', text: line.slice(1) }
    if (line.startsWith('+')) return { sign: '+', kind: 'add', text: line.slice(1) }
    return {
      sign: ' ',
      kind: 'same',
      text: line.startsWith(' ') ? line.slice(1) : line,
    }
  })
}

/**
 * A simple Python list literal, if the snippet opens with one.
 *
 * Only the unambiguous case -- `name = ["a", "b"]` of plain strings or numbers
 * on one line. Enough for the lessons that introduce indexing, which is exactly
 * where a picture beats a sentence, and it declines to guess about anything
 * else rather than drawing something wrong.
 */
export function firstListLiteral(
  code: string
): { name: string; items: string[] } | null {
  const match = /^\s*([A-Za-z_]\w*)\s*=\s*\[([^\]\[]*)\]\s*$/m.exec(code)
  if (!match) return null
  const raw = match[2].trim()
  if (!raw) return null
  const items = raw.split(',').map((piece) => piece.trim())
  if (items.length < 2 || items.length > 8) return null
  // Every item must be a plain literal; anything else and the split above is
  // not trustworthy (a comma inside a nested structure would break it).
  const literal = /^(".*"|'.*'|-?\d+(\.\d+)?|True|False|None)$/
  if (!items.every((item) => literal.test(item))) return null
  return {
    name: match[1],
    items: items.map((item) =>
      /^["']/.test(item) ? item.slice(1, -1) : item
    ),
  }
}

/**
 * The first list literal anywhere in a lesson.
 *
 * So the interactive parts work on the same values the reader has just been
 * looking at, rather than an invented example sitting next to the real one.
 */
export function firstListInLesson(
  blocks: Block[]
): { name: string; items: string[] } | null {
  for (const block of blocks) {
    if (block.kind !== 'code') continue
    const found = firstListLiteral(block.code)
    if (found) return found
  }
  return null
}
