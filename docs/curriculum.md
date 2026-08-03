# The Python curriculum

Every topic is a path from foundations to applied, specialised uses. A module
marked **[built]** has a playable exercise today; the rest are the road ahead.

This file is generated from `apps/web/src/lib/curriculum.ts` -- edit there, not
**69 modules across 6 topics — 7 built, 62 planned.**

here. The app renders the same data as a roadmap on each topic page.

## Lists

*An ordered bag of things — the workhorse of Python. Learn to build them, reach into them, reshape them, and boil them down.*

### Foundations

- **Making a list** — Create lists, add to them, and check how long they are.
- **Indexing & position** — Reach any item by its position — and why counting starts at 0.
- **Slicing** — Grab a range: the first three, the last two, every other one.

### Core skills

- **Looping over items** — Visit each item in turn with a for loop.
- **Keep only what matches** **[built]** — Build a new list of just the items that pass a test.
- **Filtering — extra drill** **[built]** — The same skill stated plainly. Good practice with no story.
- **Transforming each item** — Make a new list by changing every item the same way.
- **Sorting & reversing** — Put a list in order — by size, or by a rule of your own.

### Advanced

- **List comprehensions** — The one-line way to filter and transform at once.
- **Lists of lists (grids)** — Rows and columns: represent a board, a grid, a table.
- **Totals, highs and lows** — Sum, smallest, largest and average across a list.

### Applied & specialised

- **Leaderboards & ranking** — Turn a pile of scores into a ranked table.
- **Rows of data** — Treat a list of records as a small dataset you can query.

## Loops

*Doing something again and again — until you’re done, or until a condition flips. The heart of making a computer do the boring parts.*

### Foundations

- **Counting with for** — Repeat an action a set number of times.
- **Ranges & steps** — Count up, count down, count in twos.
- **Building up a total** — Carry a running result from one loop to the next.

### Core skills

- **Deciding inside a loop** — Do different things on different passes with an if.
- **Stopping early & skipping** — break to leave, continue to skip the rest of a pass.
- **Loop until it’s done** **[built]** — A while loop that ends when a condition finally flips.

### Advanced

- **Nested loops** — A loop inside a loop — every pair, every cell of a grid.
- **Making loops end** — Spot and fix the loop that never stops.
- **Collecting as you go** — Gather results into a list or dict across passes.

### Applied & specialised

- **Simulating turns** — Step a little world forward, one turn at a time.
- **Searching & scanning** — Sweep through data to find the thing you’re after.

## Dictionaries

*Look things up by name instead of position. Perfect for records, counts, and anything shaped like "for each X, remember Y".*

### Foundations

- **Making a dictionary** — Store values under keys you choose.
- **Lookups & .get** — Fetch a value safely, even when the key might be missing.
- **Adding & updating** — Put new keys in, change the ones already there.

### Core skills

- **Looping over a dict** — Walk the keys, the values, or both together.
- **Counting things** — Tally how many times each item shows up.
- **Check every requirement** **[built]** — Compare two dictionaries — do you have enough of each?
- **Grouping items** — Bucket records by a shared key.

### Advanced

- **Dict comprehensions** — Build a dictionary in a single expressive line.
- **Nested dictionaries** — Dicts inside dicts: records with records inside them.
- **Defaults & Counter** — setdefault and Counter for tidy tallying.

### Applied & specialised

- **Inventories & records** — Model a warehouse, a roster, a config.
- **Word frequency** — Which words appear most? A classic first analysis.

## Strings

*Text is everywhere — names, files, messages. Learn to slice it, search it, take it apart, and build it back up cleanly.*

### Foundations

- **Indexing & slicing text** — A string is a sequence of characters — reach into it.
- **Case & tidying up** — Upper, lower, and trimming stray whitespace.
- **Joining text & f-strings** — Stitch values into readable sentences.

### Core skills

- **Splitting & joining** — Break text on a separator, and put pieces back together.
- **Searching & replacing** — Find a substring, swap it out, count occurrences.
- **Parse a simple format** **[built]** — Pull structured values out of a packed string.

### Advanced

- **Formatting & alignment** — Pad, round and line things up into neat columns.
- **Checking input is valid** — Is this a number? An email-ish thing? Decide safely.
- **Building text from data** — Turn a list of records into a readable block of text.

### Applied & specialised

- **Reading line-based data** — Parse comma-separated rows into usable values.
- **Generating a report** — Assemble a formatted summary someone would actually read.

## Functions

*Name a piece of work once, use it anywhere. Functions are how programs stay readable as they grow — and how you stop repeating yourself.*

### Foundations

- **Defining & calling** — Wrap up a job and run it by name.
- **Parameters & return** — Feed a function inputs; hand a result back.
- **Default arguments** — Sensible fallbacks for arguments left out.

### Core skills

- **Functions calling functions** **[built]** — Small functions, each doing one job, working together.
- **Breaking a problem down** — Split a big task into pieces you can name.
- **Pure functions & side effects** — Why a function that just returns a value is easier to trust.

### Advanced

- **Recursion** — A function that calls itself — and knows when to stop.
- **Passing functions around** — map, filter, and sort keys: functions as arguments.
- **Lambdas** — Tiny throwaway functions, written inline.

### Applied & specialised

- **Building a small toolkit** — A handful of functions that work as a set.
- **Testing your own functions** — Prove your code does what you think it does.

## Files

*Real data lives in files. Learn to read it in, make sense of messy lines, and write clean results back out.*

### Foundations

- **Reading a file’s contents** — Get the whole thing as text you can work with.
- **Lines vs whole text** — Split a file into lines and walk them.
- **Coping with blank lines** — The trailing newline that trips everyone up.

### Core skills

- **Parse line-based data** **[built]** — Turn rows of text into names and numbers, then rank them.
- **Filtering & summarising** — Keep the rows you want; total the rest.
- **Writing output** — Produce a clean file someone else can read.

### Advanced

- **CSV handling** — Commas, quotes, headers — the real-world tabular format.
- **Lines into records** — Parse each row into a structured dictionary.
- **Handling bad data** — Skip or flag the lines that don’t fit the shape.

### Applied & specialised

- **Log analysis** — Sift a log for the events that matter.
- **A small data pipeline** — Read, clean, summarise, write — end to end.
