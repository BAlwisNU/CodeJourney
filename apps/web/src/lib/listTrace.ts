/**
 * The filter loop, executed one line at a time.
 *
 * A student reading `for quest in quests:` has to hold four things in their
 * head at once -- which item is current, what the test said about it, what the
 * collector holds, and which line runs next -- and the page shows none of them.
 * That is the actual difficulty of the lesson, and it is invisible.
 *
 * So the loop is traced ahead of time into a list of steps. Precomputed rather
 * than run live for three reasons: it can step *backwards*, which is when the
 * "wait, why was that one skipped?" moment usually happens; it is instant, with
 * no worker to wait on; and it cannot diverge from the code shown beside it,
 * because both are generated from the same threshold and operator.
 *
 * It is not a Python interpreter and does not pretend to be. It is this one
 * loop, which is the loop the lesson teaches.
 */

export type Comparison = '<' | '<='

export type TraceStep = {
  /** Index into `sourceLines` of the line about to run. */
  line: number
  /** The item under the cursor, or null outside the loop. */
  index: number | null
  /** What the `if` decided, on the step where it is evaluated. */
  test: boolean | null
  /** Indices of the items collected so far. */
  collected: number[]
  /** How many items have been decided, so the rest can be drawn as untouched. */
  decided: number
  /** What just happened, in words. */
  note: string
}

/**
 * The code being traced.
 *
 * Generated from the same inputs as the trace, so the line the cursor sits on
 * always says what the step actually did.
 */
export function sourceLines(threshold: number, op: Comparison): string[] {
  return [
    'short_ones = []',
    'for quest in quests:',
    `    if len(quest) ${op} ${threshold}:`,
    '        short_ones.append(quest)',
    'return short_ones',
  ]
}

/**
 * A threshold where the demonstration actually demonstrates.
 *
 * The median item length, which matters more than it sounds. A threshold that
 * sits between two lengths makes `<` and `<=` agree, and the whole reason the
 * operator is a control is that the lesson warns they differ -- so it is set to
 * a length some item actually has, where flipping it visibly moves that item
 * between the piles.
 *
 * The lesson's own snippet says `< 10`, and its three quests are 14, 15 and 16
 * characters, so the example as written collects nothing. Starting there would
 * open on an empty result and a control that appears broken.
 */
export function defaultThreshold(items: string[]): number {
  if (!items.length) return 10
  const lengths = items.map((item) => item.length).sort((a, b) => a - b)
  return lengths[Math.floor(lengths.length / 2)]
}

/** The range the slider should offer: every interesting answer, and no more. */
export function thresholdRange(items: string[]): { min: number; max: number } {
  const longest = items.reduce((n, item) => Math.max(n, item.length), 0)
  return { min: 1, max: longest + 4 }
}

export function passes(item: string, threshold: number, op: Comparison): boolean {
  return op === '<' ? item.length < threshold : item.length <= threshold
}

export function buildTrace(
  items: string[],
  threshold: number,
  op: Comparison
): TraceStep[] {
  const steps: TraceStep[] = []
  const collected: number[] = []

  steps.push({
    line: 0,
    index: null,
    test: null,
    collected: [],
    decided: 0,
    note: 'Start with an empty list to collect into.',
  })

  items.forEach((item, index) => {
    steps.push({
      line: 1,
      index,
      test: null,
      collected: [...collected],
      decided: index,
      note: `The loop hands you quests[${index}] — "${item}".`,
    })

    const kept = passes(item, threshold, op)
    steps.push({
      line: 2,
      index,
      test: kept,
      collected: [...collected],
      decided: index,
      note:
        `len("${item}") is ${item.length}. ` +
        `${item.length} ${op} ${threshold} is ${kept ? 'True' : 'False'}` +
        `${kept ? ' — keep it.' : ' — skip it.'}`,
    })

    if (kept) {
      collected.push(index)
      steps.push({
        line: 3,
        index,
        test: true,
        collected: [...collected],
        decided: index + 1,
        note: `append puts it on the end. The new list holds ${collected.length}.`,
      })
    }
  })

  steps.push({
    line: 4,
    index: null,
    test: null,
    collected: [...collected],
    decided: items.length,
    note: collected.length
      ? `Done — ${collected.length} of ${items.length} passed the test.`
      : 'Done — nothing passed the test. The list comes back empty.',
  })

  return steps
}
