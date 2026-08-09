import { useMemo, type ReactNode } from 'react'

import { InlineMarkdown } from '../Markdown'
import { CodeBlock } from './CodeBlock'
import { DiffBlock } from './DiffBlock'
import {
  buildPreludes,
  calloutToneFor,
  parseBlocks,
  toSections,
  type Block,
  type CalloutTone,
  type Section,
} from '../../lib/lessonBlocks'
import { lookup } from '../../lib/glossary'

/**
 * A lesson, in one scroll.
 *
 * This used to paginate: one section per page, with Back/Next and a dot per
 * page. It was a third layer of navigation on a screen that already had stage
 * tabs and sub-tabs, spent on a two-minute read -- and scrolling is the best
 * understood interaction there is. Sections are still the unit the lesson is
 * written in, and each still ends with the question that checks it; they are
 * just laid out in order rather than dealt one at a time.
 *
 * Asides become callouts, headings get a glyph, unfamiliar words get a
 * definition on hover, and code blocks run.
 *
 * Everything here works off the existing content -- no lesson had to be
 * rewritten. Where a feature needs a hint from the author (a `> **Watch out:**`
 * quote, a `# (1)` pin) the absence of the hint simply means the plain
 * rendering, which is what all 69 lessons get today.
 */

const TONE_ICON: Record<CalloutTone, string> = {
  idea: '💡',
  watch: '⚠️',
  try: '🧪',
}

/**
 * A glyph per section, chosen from the heading's own words.
 *
 * Keyed on what the headings actually say across the curriculum. An unmatched
 * heading gets a neutral dot rather than a wrong picture.
 */
const HEADING_ICONS: [RegExp, string][] = [
  [/\b(look|find|search|scan|read)\b/i, '🔍'],
  [/\b(keep|filter|only|choose|pick)\b/i, '🧹'],
  [/\b(loop|each|turn|repeat|again)\b/i, '🔁'],
  [/\b(dictionar|dict|named|record)/i, '🗂'],
  [/\b(watch|careful|mistake|trip|wrong)\b/i, '⚠️'],
  [/\b(build|make|create|write)\b/i, '🔨'],
  [/\b(count|total|sum|number)\b/i, '🔢'],
  [/\b(text|string|word|letter)\b/i, '✍️'],
  [/\b(file|line|save|open)\b/i, '📄'],
]

function iconFor(heading: string): string {
  for (const [pattern, glyph] of HEADING_ICONS) {
    if (pattern.test(heading)) return glyph
  }
  return '•'
}

/**
 * Mark the first occurrence of each glossary term in a paragraph.
 *
 * First occurrence only, and only once per term per paragraph: a page where
 * every third word is dotted is harder to read than one with none, which
 * defeats the point.
 */
function glossaryRun(
  text: string,
  seen: Set<string>,
  nextKey: () => number
): ReactNode[] {
  const out: ReactNode[] = []
  for (const part of text.split(/(\b[A-Za-z]+\b)/)) {
    const definition = lookup(part)
    const key = part.toLowerCase()
    if (definition && !seen.has(key)) {
      seen.add(key)
      out.push(
        <abbr key={nextKey()} className="gloss" title={definition}>
          {part}
        </abbr>
      )
    } else {
      out.push(part)
    }
  }
  return out
}

/**
 * A paragraph, with inline markup AND glossary marking.
 *
 * These have to happen in one pass. Doing markup first leaves React elements
 * that cannot be scanned for words; doing glossary first would mark terms
 * inside `code` spans, where they are identifiers rather than prose. So the
 * text is split on markup, and only the plain runs between the spans are
 * offered to the glossary.
 */
const INLINE = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g

function Paragraph({ text }: { text: string }) {
  const seen = new Set<string>()
  const out: ReactNode[] = []
  let last = 0
  let key = 0
  let match: RegExpExecArray | null

  INLINE.lastIndex = 0
  while ((match = INLINE.exec(text)) !== null) {
    if (match.index > last) {
      out.push(...glossaryRun(text.slice(last, match.index), seen, () => key++))
    }
    const token = match[0]
    if (token.startsWith('`')) out.push(<code key={key++}>{token.slice(1, -1)}</code>)
    else if (token.startsWith('**')) out.push(<strong key={key++}>{token.slice(2, -2)}</strong>)
    else out.push(<em key={key++}>{token.slice(1, -1)}</em>)
    last = match.index + token.length
  }
  if (last < text.length) {
    out.push(...glossaryRun(text.slice(last), seen, () => key++))
  }
  return <p>{out}</p>
}

function Callout({
  tone,
  title,
  body,
}: {
  tone: CalloutTone
  title: string
  body: string[]
}) {
  return (
    <aside className={`callout callout-${tone}`}>
      <p className="callout-title">
        <span aria-hidden>{TONE_ICON[tone]}</span> {title}
      </p>
      {body.map((line, i) => (
        <p key={i}>
          <InlineMarkdown source={line} />
        </p>
      ))}
    </aside>
  )
}

function renderBlocks(
  blocks: Block[],
  preludes: Map<Block, string>
): ReactNode[] {
  const out: ReactNode[] = []

  blocks.forEach((block, index) => {
    if (block.kind === 'code' && block.lang === 'diff') {
      out.push(<DiffBlock key={index} code={block.code} />)
      return
    }

    if (block.kind === 'code') {
      // A numbered list straight after an annotated block is its notes.
      const next = blocks[index + 1]
      const notes =
        block.annotations.length > 0 && next?.kind === 'list' && next.ordered
          ? next.items
          : undefined
      out.push(
        <CodeBlock
          key={index}
          code={block.code}
          lang={block.lang}
          annotations={block.annotations}
          notes={notes}
          prelude={preludes.get(block) ?? ''}
        />
      )
      return
    }

    if (block.kind === 'list') {
      // Skip a list already consumed as the previous block's annotations.
      const prev = blocks[index - 1]
      if (prev?.kind === 'code' && prev.annotations.length > 0 && block.ordered) return
      const items = block.items.map((item, i) => (
        <li key={i}>
          <InlineMarkdown source={item} />
        </li>
      ))
      out.push(
        block.ordered ? <ol key={index}>{items}</ol> : <ul key={index}>{items}</ul>
      )
      return
    }

    if (block.kind === 'callout') {
      out.push(
        <Callout key={index} tone={block.tone} title={block.title} body={block.body} />
      )
      return
    }

    if (block.kind === 'para') {
      out.push(<Paragraph key={index} text={block.text} />)
      return
    }

    if (block.kind === 'heading') {
      out.push(<h4 key={index}>{block.text}</h4>)
    }
  })

  return out
}

/** One section, rendered as a page. */
function Page({
  section,
  preludes,
  checkpoint,
}: {
  section: Section
  preludes: Map<Block, string>
  /** The question that belongs to this section, if the lesson has one spare. */
  checkpoint?: ReactNode
}) {
  // A section with no heading is the lesson's opening -- it has nothing to
  // title, and the panel above already carries the lesson's own title.
  if (!section.heading) {
    return (
      <section className="ls">
        {renderBlocks(section.blocks, preludes)}
        {checkpoint}
      </section>
    )
  }

  const tone = calloutToneFor(section.heading)
  if (tone) {
    // The author wrote an aside as a heading; render it as one.
    return (
      <section className="ls">
        <Callout
          tone={tone}
          title={section.heading}
          body={section.blocks
            .filter((b): b is Extract<Block, { kind: 'para' }> => b.kind === 'para')
            .map((b) => b.text)}
        />
        {renderBlocks(
          section.blocks.filter((b) => b.kind !== 'para'),
          preludes
        )}
        {checkpoint}
      </section>
    )
  }

  return (
    <section className="ls">
      <h3>
        <span className="ls-icon" aria-hidden>
          {iconFor(section.heading)}
        </span>
        <span className="ls-title">{section.heading}</span>
      </h3>
      <div className="ls-body">{renderBlocks(section.blocks, preludes)}</div>
      {checkpoint}
    </section>
  )
}

export function LessonBody({
  source,
  checkpointFor,
}: {
  source: string
  /**
   * The question to ask after headed section `n` (1-based), if any.
   *
   * A callback rather than a list, because which questions are spare is the
   * Plan page's business -- it owns the quiz and has to not ask the same thing
   * twice.
   */
  checkpointFor?: (n: number) => ReactNode
}) {
  const blocks = useMemo(() => parseBlocks(source), [source])
  const sections = useMemo(() => toSections(blocks), [blocks])
  const preludes = useMemo(() => buildPreludes(blocks), [blocks])

  if (!sections.length) return null

  let headed = 0

  return (
    <div className="lesson-body md">
      {sections.map((section, i) => {
        if (section.heading) headed += 1
        return (
          <Page
            key={i}
            section={section}
            preludes={preludes}
            checkpoint={section.heading ? checkpointFor?.(headed) : undefined}
          />
        )
      })}
    </div>
  )
}
