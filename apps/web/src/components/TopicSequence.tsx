import { Fragment } from 'react'
import { Link } from 'react-router-dom'

import type { SeqNode } from '../lib/curriculum'
import type { DashboardBranch } from '../lib/types'

/**
 * A topic's modules as a linear sequence -- episodes one after another, joined
 * by a single connecting line, basics on the left through to applied on the
 * right.
 *
 * Every built lesson is a link, whatever its state and wherever it sits in the
 * line: a learner can start at any point, not just the next one. Each episode
 * shows where it stands -- Completed, In progress, or ready to Start -- and a
 * not-yet-built module is marked Planned.
 *
 * A started-but-unfinished lesson opens straight into the editor to carry on; a
 * fresh one opens the lesson/warm-up first. The line is pure CSS, so unlike the
 * old branching tree there's nothing to measure.
 */
export function TopicSequence({
  nodes,
  branchesBySlug,
}: {
  nodes: SeqNode[]
  /** slug of a built module -> the practice branches hanging off it. */
  branchesBySlug?: Map<string, DashboardBranch[]>
}) {
  type Item =
    | { kind: 'tier'; label: string; key: string }
    | { kind: 'ep'; node: SeqNode; num: number }

  const items: Item[] = []
  let prevTier: string | null = null
  let episode = 0
  for (const node of nodes) {
    if (node.tier !== prevTier) {
      items.push({ kind: 'tier', label: node.tierLabel, key: `tier-${node.tier}` })
      prevTier = node.tier
    }
    episode += 1
    items.push({ kind: 'ep', node, num: episode })
  }

  // Branches hang below their episode (absolutely, so they don't stretch the
  // row). Reserve the vertical room the whole tree needs -- practice built ON
  // practice nests deeper, so this counts descendants, not just direct children.
  const maxBranches = branchesBySlug
    ? nodes.reduce(
        (m, n) => Math.max(m, n.slug ? countTree(branchesBySlug, n.slug) : 0),
        0
      )
    : 0

  return (
    <div
      className="seq"
      style={maxBranches ? { paddingBottom: 20 + maxBranches * 66 } : undefined}
    >
      <div className="seq-track">
        {items.map((item, i) => (
          <Fragment key={item.kind === 'tier' ? item.key : item.node.id}>
            {i > 0 && <span className="seq-link" aria-hidden />}
            {item.kind === 'tier' ? (
              <span className="seq-tier">{item.label}</span>
            ) : (
              // An episode plus any practice branched off it. A branch can't sit
              // to the right -- that space belongs to the next lesson in the line
              // -- so it hangs below. Practice built FROM a branch nests under
              // that branch rather than replacing it, so the whole tree shows.
              <div className="seq-col">
                <Episode node={item.node} num={item.num} />
                {item.node.slug &&
                  branchesBySlug &&
                  countTree(branchesBySlug, item.node.slug) > 0 && (
                    <div className="seq-branches">
                      <BranchTree
                        branchesBySlug={branchesBySlug}
                        parentSlug={item.node.slug}
                        depth={0}
                      />
                    </div>
                  )}
              </div>
            )}
          </Fragment>
        ))}
      </div>
    </div>
  )
}

/** Total branches beneath a slug, counting practice built on practice too.
 *  Depth-capped so a stray cycle in the data can never loop forever. */
function countTree(
  branchesBySlug: Map<string, DashboardBranch[]>,
  slug: string,
  depth = 0
): number {
  if (depth > 8) return 0
  const kids = branchesBySlug.get(slug) ?? []
  return kids.reduce(
    (n, b) => n + 1 + countTree(branchesBySlug, b.slug, depth + 1),
    0
  )
}

/** The branches under one slug, each followed by its own sub-branches, indented
 *  a step deeper so "made from that" reads as nesting rather than a flat list. */
function BranchTree({
  branchesBySlug,
  parentSlug,
  depth,
}: {
  branchesBySlug: Map<string, DashboardBranch[]>
  parentSlug: string
  depth: number
}) {
  if (depth > 8) return null
  const kids = branchesBySlug.get(parentSlug) ?? []
  return (
    <>
      {kids.map((b) => (
        <Fragment key={b.slug}>
          <Link
            className={`seq-branch ${b.status}`}
            to={`/exercise/${b.slug}`}
            style={depth ? { marginLeft: depth * 16 } : undefined}
          >
            <span className="seq-branch-mark" aria-hidden>
              {b.status === 'solved' ? '✓' : '+'}
            </span>
            <span className="seq-branch-body">
              <span className="seq-branch-title">{b.title}</span>
              <span className="seq-branch-tag">
                {depth === 0 ? 'your practice' : 'built from the one above'}
              </span>
            </span>
          </Link>
          <BranchTree
            branchesBySlug={branchesBySlug}
            parentSlug={b.slug}
            depth={depth + 1}
          />
        </Fragment>
      ))}
    </>
  )
}

const STATUS_LABEL: Record<SeqNode['state'], string> = {
  done: 'Completed',
  in_progress: 'In progress',
  available: 'Start',
  planned: 'Planned',
}

function Episode({ node, num }: { node: SeqNode; num: number }) {
  const inner = (
    <>
      <span className="seq-num" aria-hidden>
        {node.state === 'done' ? '✓' : num}
      </span>
      <span className="seq-body">
        <span className="seq-title">{node.title}</span>
        <span className="seq-blurb">{node.blurb}</span>
        <span className={`seq-status ${node.state}`}>{STATUS_LABEL[node.state]}</span>
      </span>
    </>
  )

  if (!node.slug) {
    return (
      <div className="seq-ep planned" aria-disabled>
        {inner}
      </div>
    )
  }

  // Carry on where you left off: a started lesson opens the editor directly; a
  // fresh one goes through the lesson and warm-up first.
  const href =
    node.state === 'in_progress' || node.state === 'done'
      ? `/exercise/${node.slug}`
      : `/exercise/${node.slug}/plan`

  return (
    <Link className={`seq-ep ${node.state}`} to={href}>
      {inner}
    </Link>
  )
}
