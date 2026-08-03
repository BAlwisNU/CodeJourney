/**
 * The Python curriculum: for each topic, a full path of modules from
 * foundations through to applied, specialised uses.
 *
 * A `module` is one learning unit -- a lesson, its quiz, its warm-up, and the
 * exercise you write. When a module has a `slug`, that exercise is built and
 * playable now; a module with no slug is on the roadmap, shown so a learner can
 * see where the path leads before it's finished. That honesty is deliberate:
 * the same reason the locked languages say "coming soon" rather than linking to
 * nothing.
 *
 * This is content design, not user data, so it lives here as static data. When
 * an exercise for a planned module is built, give the module its `slug` and it
 * becomes playable -- a one-line change, no schema migration.
 *
 * The full curriculum is also written up in docs/curriculum.md for the content
 * track to work through.
 */

export type Level = 'foundation' | 'core' | 'advanced' | 'applied'

export type Module = {
  id: string
  title: string
  blurb: string
  level: Level
  /** Present when a built exercise backs this module. */
  slug?: string
}

export type TopicCurriculum = {
  key: string // matches an exercise `concept`
  label: string
  intro: string
  modules: Module[]
}

export const LEVELS: { key: Level; label: string; hint: string }[] = [
  { key: 'foundation', label: 'Foundations', hint: 'Start here — the pieces everything else builds on.' },
  { key: 'core', label: 'Core skills', hint: 'The moves you’ll reach for every day.' },
  { key: 'advanced', label: 'Advanced', hint: 'Sharper tools, once the basics feel easy.' },
  { key: 'applied', label: 'Applied & specialised', hint: 'Put it to work on real-shaped problems.' },
]

export const CURRICULUM: TopicCurriculum[] = [
  {
    key: 'lists',
    label: 'Lists',
    intro: 'An ordered bag of things — the workhorse of Python. Learn to build them, reach into them, reshape them, and boil them down.',
    modules: [
      { id: 'lists-make', slug: 'lists-make', level: 'foundation', title: 'Making a list', blurb: 'Create lists, add to them, and check how long they are.' },
      { id: 'lists-index', slug: 'lists-index', level: 'foundation', title: 'Indexing & position', blurb: 'Reach any item by its position — and why counting starts at 0.' },
      { id: 'lists-slice', slug: 'lists-slice', level: 'foundation', title: 'Slicing', blurb: 'Grab a range: the first three, the last two, every other one.' },
      { id: 'lists-loop', slug: 'lists-loop', level: 'core', title: 'Looping over items', blurb: 'Visit each item in turn with a for loop.' },
      { id: 'lists-filter', level: 'core', title: 'Keep only what matches', blurb: 'Build a new list of just the items that pass a test.', slug: 'expired-quests' },
      { id: 'lists-filter-plain', level: 'core', title: 'Filtering — extra drill', blurb: 'The same skill stated plainly. Good practice with no story.', slug: 'filter-records-generic' },
      { id: 'lists-map', slug: 'lists-map', level: 'core', title: 'Transforming each item', blurb: 'Make a new list by changing every item the same way.' },
      { id: 'lists-sort', slug: 'lists-sort', level: 'core', title: 'Sorting & reversing', blurb: 'Put a list in order — by size, or by a rule of your own.' },
      { id: 'lists-comp', slug: 'lists-comp', level: 'advanced', title: 'List comprehensions', blurb: 'The one-line way to filter and transform at once.' },
      { id: 'lists-nested', slug: 'lists-nested', level: 'advanced', title: 'Lists of lists (grids)', blurb: 'Rows and columns: represent a board, a grid, a table.' },
      { id: 'lists-agg', slug: 'lists-agg', level: 'advanced', title: 'Totals, highs and lows', blurb: 'Sum, smallest, largest and average across a list.' },
      { id: 'lists-rank', slug: 'lists-rank', level: 'applied', title: 'Leaderboards & ranking', blurb: 'Turn a pile of scores into a ranked table.' },
      { id: 'lists-table', slug: 'lists-table', level: 'applied', title: 'Rows of data', blurb: 'Treat a list of records as a small dataset you can query.' },
    ],
  },
  {
    key: 'loops',
    label: 'Loops',
    intro: 'Doing something again and again — until you’re done, or until a condition flips. The heart of making a computer do the boring parts.',
    modules: [
      { id: 'loops-for', slug: 'loops-for', level: 'foundation', title: 'Counting with for', blurb: 'Repeat an action a set number of times.' },
      { id: 'loops-range', slug: 'loops-range', level: 'foundation', title: 'Ranges & steps', blurb: 'Count up, count down, count in twos.' },
      { id: 'loops-accum', slug: 'loops-accum', level: 'foundation', title: 'Building up a total', blurb: 'Carry a running result from one loop to the next.' },
      { id: 'loops-cond', slug: 'loops-cond', level: 'core', title: 'Deciding inside a loop', blurb: 'Do different things on different passes with an if.' },
      { id: 'loops-break', slug: 'loops-break', level: 'core', title: 'Stopping early & skipping', blurb: 'break to leave, continue to skip the rest of a pass.' },
      { id: 'loops-until', level: 'core', title: 'Loop until it’s done', blurb: 'A while loop that ends when a condition finally flips.', slug: 'boss-fight' },
      { id: 'loops-nested', slug: 'loops-nested', level: 'advanced', title: 'Nested loops', blurb: 'A loop inside a loop — every pair, every cell of a grid.' },
      { id: 'loops-terminate', slug: 'loops-terminate', level: 'advanced', title: 'Making loops end', blurb: 'Spot and fix the loop that never stops.' },
      { id: 'loops-collect', slug: 'loops-collect', level: 'advanced', title: 'Collecting as you go', blurb: 'Gather results into a list or dict across passes.' },
      { id: 'loops-sim', slug: 'loops-sim', level: 'applied', title: 'Simulating turns', blurb: 'Step a little world forward, one turn at a time.' },
      { id: 'loops-scan', slug: 'loops-scan', level: 'applied', title: 'Searching & scanning', blurb: 'Sweep through data to find the thing you’re after.' },
    ],
  },
  {
    key: 'dicts',
    label: 'Dictionaries',
    intro: 'Look things up by name instead of position. Perfect for records, counts, and anything shaped like "for each X, remember Y".',
    modules: [
      { id: 'dicts-make', slug: 'dicts-make', level: 'foundation', title: 'Making a dictionary', blurb: 'Store values under keys you choose.' },
      { id: 'dicts-get', slug: 'dicts-get', level: 'foundation', title: 'Lookups & .get', blurb: 'Fetch a value safely, even when the key might be missing.' },
      { id: 'dicts-update', slug: 'dicts-update', level: 'foundation', title: 'Adding & updating', blurb: 'Put new keys in, change the ones already there.' },
      { id: 'dicts-iter', slug: 'dicts-iter', level: 'core', title: 'Looping over a dict', blurb: 'Walk the keys, the values, or both together.' },
      { id: 'dicts-count', slug: 'dicts-count', level: 'core', title: 'Counting things', blurb: 'Tally how many times each item shows up.' },
      { id: 'dicts-require', level: 'core', title: 'Check every requirement', blurb: 'Compare two dictionaries — do you have enough of each?', slug: 'can-i-craft-it' },
      { id: 'dicts-group', slug: 'dicts-group', level: 'core', title: 'Grouping items', blurb: 'Bucket records by a shared key.' },
      { id: 'dicts-comp', slug: 'dicts-comp', level: 'advanced', title: 'Dict comprehensions', blurb: 'Build a dictionary in a single expressive line.' },
      { id: 'dicts-nested', slug: 'dicts-nested', level: 'advanced', title: 'Nested dictionaries', blurb: 'Dicts inside dicts: records with records inside them.' },
      { id: 'dicts-default', slug: 'dicts-default', level: 'advanced', title: 'Defaults & Counter', blurb: 'setdefault and Counter for tidy tallying.' },
      { id: 'dicts-inventory', slug: 'dicts-inventory', level: 'applied', title: 'Inventories & records', blurb: 'Model a warehouse, a roster, a config.' },
      { id: 'dicts-freq', slug: 'dicts-freq', level: 'applied', title: 'Word frequency', blurb: 'Which words appear most? A classic first analysis.' },
    ],
  },
  {
    key: 'strings',
    label: 'Strings',
    intro: 'Text is everywhere — names, files, messages. Learn to slice it, search it, take it apart, and build it back up cleanly.',
    modules: [
      { id: 'str-index', slug: 'str-index', level: 'foundation', title: 'Indexing & slicing text', blurb: 'A string is a sequence of characters — reach into it.' },
      { id: 'str-case', slug: 'str-case', level: 'foundation', title: 'Case & tidying up', blurb: 'Upper, lower, and trimming stray whitespace.' },
      { id: 'str-fstring', slug: 'str-fstring', level: 'foundation', title: 'Joining text & f-strings', blurb: 'Stitch values into readable sentences.' },
      { id: 'str-split', slug: 'str-split', level: 'core', title: 'Splitting & joining', blurb: 'Break text on a separator, and put pieces back together.' },
      { id: 'str-search', slug: 'str-search', level: 'core', title: 'Searching & replacing', blurb: 'Find a substring, swap it out, count occurrences.' },
      { id: 'str-parse', level: 'core', title: 'Parse a simple format', blurb: 'Pull structured values out of a packed string.', slug: 'save-game-names' },
      { id: 'str-format', slug: 'str-format', level: 'advanced', title: 'Formatting & alignment', blurb: 'Pad, round and line things up into neat columns.' },
      { id: 'str-validate', slug: 'str-validate', level: 'advanced', title: 'Checking input is valid', blurb: 'Is this a number? An email-ish thing? Decide safely.' },
      { id: 'str-build', slug: 'str-build', level: 'advanced', title: 'Building text from data', blurb: 'Turn a list of records into a readable block of text.' },
      { id: 'str-csv', slug: 'str-csv', level: 'applied', title: 'Reading line-based data', blurb: 'Parse comma-separated rows into usable values.' },
      { id: 'str-report', slug: 'str-report', level: 'applied', title: 'Generating a report', blurb: 'Assemble a formatted summary someone would actually read.' },
    ],
  },
  {
    key: 'functions',
    label: 'Functions',
    intro: 'Name a piece of work once, use it anywhere. Functions are how programs stay readable as they grow — and how you stop repeating yourself.',
    modules: [
      { id: 'fn-define', slug: 'fn-define', level: 'foundation', title: 'Defining & calling', blurb: 'Wrap up a job and run it by name.' },
      { id: 'fn-params', slug: 'fn-params', level: 'foundation', title: 'Parameters & return', blurb: 'Feed a function inputs; hand a result back.' },
      { id: 'fn-defaults', slug: 'fn-defaults', level: 'foundation', title: 'Default arguments', blurb: 'Sensible fallbacks for arguments left out.' },
      { id: 'fn-compose', level: 'core', title: 'Functions calling functions', blurb: 'Small functions, each doing one job, working together.', slug: 'character-sheet' },
      { id: 'fn-decompose', slug: 'fn-decompose', level: 'core', title: 'Breaking a problem down', blurb: 'Split a big task into pieces you can name.' },
      { id: 'fn-pure', slug: 'fn-pure', level: 'core', title: 'Pure functions & side effects', blurb: 'Why a function that just returns a value is easier to trust.' },
      { id: 'fn-recursion', slug: 'fn-recursion', level: 'advanced', title: 'Recursion', blurb: 'A function that calls itself — and knows when to stop.' },
      { id: 'fn-higher', slug: 'fn-higher', level: 'advanced', title: 'Passing functions around', blurb: 'map, filter, and sort keys: functions as arguments.' },
      { id: 'fn-lambda', slug: 'fn-lambda', level: 'advanced', title: 'Lambdas', blurb: 'Tiny throwaway functions, written inline.' },
      { id: 'fn-library', slug: 'fn-library', level: 'applied', title: 'Building a small toolkit', blurb: 'A handful of functions that work as a set.' },
      { id: 'fn-test', slug: 'fn-test', level: 'applied', title: 'Testing your own functions', blurb: 'Prove your code does what you think it does.' },
    ],
  },
  {
    key: 'file_io',
    label: 'Files',
    intro: 'Real data lives in files. Learn to read it in, make sense of messy lines, and write clean results back out.',
    modules: [
      { id: 'file-read', slug: 'file-read', level: 'foundation', title: 'Reading a file’s contents', blurb: 'Get the whole thing as text you can work with.' },
      { id: 'file-lines', slug: 'file-lines', level: 'foundation', title: 'Lines vs whole text', blurb: 'Split a file into lines and walk them.' },
      { id: 'file-trailing', slug: 'file-trailing', level: 'foundation', title: 'Coping with blank lines', blurb: 'The trailing newline that trips everyone up.' },
      { id: 'file-parse', level: 'core', title: 'Parse line-based data', blurb: 'Turn rows of text into names and numbers, then rank them.', slug: 'high-score-table' },
      { id: 'file-summarise', slug: 'file-summarise', level: 'core', title: 'Filtering & summarising', blurb: 'Keep the rows you want; total the rest.' },
      { id: 'file-write', slug: 'file-write', level: 'core', title: 'Writing output', blurb: 'Produce a clean file someone else can read.' },
      { id: 'file-csv', slug: 'file-csv', level: 'advanced', title: 'CSV handling', blurb: 'Commas, quotes, headers — the real-world tabular format.' },
      { id: 'file-records', slug: 'file-records', level: 'advanced', title: 'Lines into records', blurb: 'Parse each row into a structured dictionary.' },
      { id: 'file-robust', slug: 'file-robust', level: 'advanced', title: 'Handling bad data', blurb: 'Skip or flag the lines that don’t fit the shape.' },
      { id: 'file-log', slug: 'file-log', level: 'applied', title: 'Log analysis', blurb: 'Sift a log for the events that matter.' },
      { id: 'file-pipeline', slug: 'file-pipeline', level: 'applied', title: 'A small data pipeline', blurb: 'Read, clean, summarise, write — end to end.' },
    ],
  },
]

export const CURRICULUM_BY_KEY: Record<string, TopicCurriculum> = Object.fromEntries(
  CURRICULUM.map((t) => [t.key, t])
)

/** Modules with a built exercise, i.e. playable right now. */
export function availableCount(topic: TopicCurriculum): number {
  return topic.modules.filter((m) => m.slug).length
}

// --- building tiers for the tree view --------------------------------------

export type ModuleUiState =
  | 'done'
  | 'in_progress'
  | 'available'
  | 'planned'

// --- flat sequence for the "episodes one after another" view ---------------

export type SeqNode = {
  id: string
  title: string
  blurb: string
  state: ModuleUiState
  slug?: string
  tier: Level
  tierLabel: string
}

/** The learner's status for a built exercise, or undefined if not built. */
export type ExerciseStatus = 'solved' | 'in_progress' | 'not_started' | undefined

/**
 * The topic's modules as a single ordered sequence -- episodes one after
 * another, foundations first. The module array is already authored in teaching
 * order, so the sequence is simply that order with each item's state and tier
 * attached. `tier`/`tierLabel` let the sequence show waypoints without breaking
 * the single line.
 *
 * `statusOf` maps a built exercise's slug to the learner's progress, so an
 * episode can read done / in-progress / not-yet-started; modules with no
 * exercise are 'planned'.
 */
export function buildSequence(
  topic: TopicCurriculum,
  statusOf: (slug: string) => ExerciseStatus
): SeqNode[] {
  const labelOf = Object.fromEntries(LEVELS.map((l) => [l.key, l.label]))
  const toState = (slug?: string): ModuleUiState => {
    if (!slug) return 'planned'
    const status = statusOf(slug)
    if (status === 'solved') return 'done'
    if (status === 'in_progress') return 'in_progress'
    return 'available'
  }
  return topic.modules.map((m) => ({
    id: m.id,
    title: m.title,
    blurb: m.blurb,
    slug: m.slug,
    tier: m.level,
    tierLabel: labelOf[m.level],
    state: toState(m.slug),
  }))
}
