/**
 * One-line definitions for the words a first-week learner trips over.
 *
 * Deliberately small and hand-written. A dictionary big enough to cover
 * everything would end up defining terms in terms of other undefined terms,
 * which is how glossaries become useless; this covers the vocabulary these
 * lessons actually introduce, in the plainest words available.
 *
 * Matching is whole-word and case-insensitive, and only the first occurrence in
 * a paragraph is marked -- a page where every third word is dotted is harder to
 * read than one with none.
 */
export const GLOSSARY: Record<string, string> = {
  list: 'An ordered collection of things. Positions start at 0.',
  dictionary: 'A collection of values stored under names you choose, rather than positions.',
  loop: 'Doing the same thing to each item, or until a condition changes.',
  function: 'A named piece of work you can run again by calling its name.',
  string: 'Text. Anything inside quotes.',
  index: 'The position of an item, counting from 0.',
  filtering: 'Building a new collection of only the items that pass a test.',
  boolean: 'A value that is either True or False.',
  argument: 'A value you hand to a function when you call it.',
  variable: 'A name that refers to a value.',
  traceback: "Python's report of what went wrong and where.",
  integer: 'A whole number, with no decimal point.',
}

const TERMS = Object.keys(GLOSSARY).sort((a, b) => b.length - a.length)

/** The glossary term at the start of `word`, if any. Punctuation is ignored. */
export function lookup(word: string): string | null {
  const bare = word.replace(/[^A-Za-z]/g, '').toLowerCase()
  if (!bare) return null
  return GLOSSARY[bare] ?? null
}

export function hasTerms(text: string): boolean {
  const lower = text.toLowerCase()
  return TERMS.some((term) => new RegExp(`\\b${term}\\b`).test(lower))
}
