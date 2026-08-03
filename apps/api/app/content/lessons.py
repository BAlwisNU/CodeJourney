"""The rest of the Python curriculum -- one small, focused exercise per module.

These back the modules that the roadmap shows as "planned" until built. Each is
deliberately small: a single skill, a clear task, three tests, a reference
solution that test_content.py runs through the real harness. Slugs match the
curriculum module ids in apps/web/src/lib/curriculum.ts one-to-one, so every
module on the dashboard is a real, openable lesson.

Kept plain (Theme.GENERIC): these teach the mechanics of a concept directly.
The themed exercises in games.py sit alongside them for the same concepts.
"""

from ..models import Concept, Theme, ThemeVariant
from ._shared import ex, t

_order = 100


def L(*, slug, title, concept, entrypoint, prompt, starter, tests, hints, solution):
    global _order
    _order += 1
    return ex(
        slug=slug,
        title=title,
        theme=Theme.GENERIC,
        variant=ThemeVariant.GENERIC,
        concept=concept,
        entrypoint=entrypoint,
        prompt=prompt,
        starter=starter,
        tests=tests,
        hints=hints,
        solution=solution,
        order=_order,
    )


def _h(l2, l3):
    return {"2": l2, "3": l3}


LI, LO, DI, ST, FN, FI = (
    Concept.LISTS,
    Concept.LOOPS,
    Concept.DICTS,
    Concept.STRINGS,
    Concept.FUNCTIONS,
    Concept.FILE_IO,
)

LESSONS = [
    # ===================================================================== LISTS
    L(
        slug="lists-make", title="Making a list", concept=LI, entrypoint="build_list",
        prompt="Write `build_list(a, b, c)` that returns a list holding the three "
               "values, in that order.\n\n```python\nbuild_list(1, 2, 3)  # -> [1, 2, 3]\n```",
        starter="def build_list(a, b, c):\n    # Put the three values into one list.\n    return []\n",
        tests=[t("three numbers", [1, 2, 3], [1, 2, 3]),
               t("words", ["a", "b", "c"], ["a", "b", "c"]),
               t("order matters", [3, 1, 2], [3, 1, 2], hidden=True)],
        hints=_h("Square brackets make a list: `[a, b, c]`.",
                 "Just return `[a, b, c]` — the values in order."),
        solution="def build_list(a, b, c):\n    return [a, b, c]\n",
    ),
    L(
        slug="lists-index", title="Indexing & position", concept=LI, entrypoint="first_and_last",
        prompt="Write `first_and_last(items)` returning a list of just the first and "
               "last items.\n\n```python\nfirst_and_last([10, 20, 30])  # -> [10, 30]\n```",
        starter="def first_and_last(items):\n    # The first is at 0, the last is at -1.\n    return []\n",
        tests=[t("three", [[10, 20, 30]], [10, 30]),
               t("two", [["x", "y"]], ["x", "y"]),
               t("single item", [[7]], [7, 7], hidden=True)],
        hints=_h("`items[0]` is the first, `items[-1]` is the last.",
                 "Return `[items[0], items[-1]]`."),
        solution="def first_and_last(items):\n    return [items[0], items[-1]]\n",
    ),
    L(
        slug="lists-slice", title="Slicing", concept=LI, entrypoint="first_n",
        prompt="Write `first_n(items, n)` returning the first `n` items.\n\n"
               "```python\nfirst_n([1, 2, 3, 4], 2)  # -> [1, 2]\n```",
        starter="def first_n(items, n):\n    # A slice items[:n] takes the first n.\n    return []\n",
        tests=[t("first two", [[1, 2, 3, 4], 2], [1, 2]),
               t("more than there are", [[1, 2], 5], [1, 2]),
               t("none", [[1, 2, 3], 0], [], hidden=True)],
        hints=_h("`items[:n]` is the slice up to position n.",
                 "Return `items[:n]`."),
        solution="def first_n(items, n):\n    return items[:n]\n",
    ),
    L(
        slug="lists-loop", title="Looping over items", concept=LI, entrypoint="count_positive",
        prompt="Write `count_positive(nums)` returning how many numbers are greater "
               "than 0.\n\n```python\ncount_positive([-1, 2, 0, 5])  # -> 2\n```",
        starter="def count_positive(nums):\n    count = 0\n    # Loop and count the ones above 0.\n    return count\n",
        tests=[t("mixed", [[-1, 2, 0, 5]], 2),
               t("all positive", [[1, 2, 3]], 3),
               t("none positive", [[-1, 0]], 0, hidden=True)],
        hints=_h("Loop over nums; add 1 to count when the number is > 0.",
                 "`for n in nums:` then `if n > 0: count += 1`."),
        solution="def count_positive(nums):\n    count = 0\n    for n in nums:\n        if n > 0:\n            count += 1\n    return count\n",
    ),
    L(
        slug="lists-map", title="Transforming each item", concept=LI, entrypoint="add_one",
        prompt="Write `add_one(nums)` returning a new list with 1 added to every "
               "number.\n\n```python\nadd_one([1, 2, 3])  # -> [2, 3, 4]\n```",
        starter="def add_one(nums):\n    result = []\n    # Add 1 to each number.\n    return result\n",
        tests=[t("basic", [[1, 2, 3]], [2, 3, 4]),
               t("negatives", [[-1, 0]], [0, 1]),
               t("empty", [[]], [], hidden=True)],
        hints=_h("Start with an empty list and append n + 1 for each n.",
                 "`for n in nums: result.append(n + 1)`."),
        solution="def add_one(nums):\n    return [n + 1 for n in nums]\n",
    ),
    L(
        slug="lists-sort", title="Sorting & reversing", concept=LI, entrypoint="sort_desc",
        prompt="Write `sort_desc(nums)` returning the numbers sorted from largest to "
               "smallest.\n\n```python\nsort_desc([3, 1, 2])  # -> [3, 2, 1]\n```",
        starter="def sort_desc(nums):\n    # sorted(nums, reverse=True) orders big-to-small.\n    return []\n",
        tests=[t("basic", [[3, 1, 2]], [3, 2, 1]),
               t("already sorted", [[5, 4]], [5, 4]),
               t("with duplicates", [[1, 3, 1]], [3, 1, 1], hidden=True)],
        hints=_h("`sorted(nums)` sorts ascending; add `reverse=True`.",
                 "Return `sorted(nums, reverse=True)`."),
        solution="def sort_desc(nums):\n    return sorted(nums, reverse=True)\n",
    ),
    L(
        slug="lists-comp", title="List comprehensions", concept=LI, entrypoint="evens",
        prompt="Write `evens(nums)` returning only the even numbers, in order. Try a "
               "list comprehension.\n\n```python\nevens([1, 2, 3, 4])  # -> [2, 4]\n```",
        starter="def evens(nums):\n    # [n for n in nums if ...]\n    return []\n",
        tests=[t("basic", [[1, 2, 3, 4]], [2, 4]),
               t("all odd", [[1, 3, 5]], []),
               t("with zero", [[0, 1, 2]], [0, 2], hidden=True)],
        hints=_h("A number is even when `n % 2 == 0`.",
                 "`[n for n in nums if n % 2 == 0]`."),
        solution="def evens(nums):\n    return [n for n in nums if n % 2 == 0]\n",
    ),
    L(
        slug="lists-nested", title="Lists of lists (grids)", concept=LI, entrypoint="cell",
        prompt="A grid is a list of rows. Write `cell(grid, r, c)` returning the value "
               "at row `r`, column `c`.\n\n```python\ncell([[1, 2], [3, 4]], 1, 0)  # -> 3\n```",
        starter="def cell(grid, r, c):\n    # grid[r] is a row; [c] picks the column.\n    return None\n",
        tests=[t("bottom left", [[[1, 2], [3, 4]], 1, 0], 3),
               t("top right", [[[1, 2], [3, 4]], 0, 1], 2),
               t("single cell", [[[9]], 0, 0], 9, hidden=True)],
        hints=_h("First pick the row: `grid[r]`. Then the column of that row.",
                 "Return `grid[r][c]`."),
        solution="def cell(grid, r, c):\n    return grid[r][c]\n",
    ),
    L(
        slug="lists-agg", title="Totals, highs and lows", concept=LI, entrypoint="high_low",
        prompt="Write `high_low(nums)` returning a list of the smallest and largest "
               "numbers: `[min, max]`.\n\n```python\nhigh_low([3, 7, 1])  # -> [1, 7]\n```",
        starter="def high_low(nums):\n    # min(nums) and max(nums) do the work.\n    return []\n",
        tests=[t("basic", [[3, 7, 1]], [1, 7]),
               t("negatives", [[-5, -1, -9]], [-9, -1]),
               t("single", [[4]], [4, 4], hidden=True)],
        hints=_h("`min(nums)` and `max(nums)` give the smallest and largest.",
                 "Return `[min(nums), max(nums)]`."),
        solution="def high_low(nums):\n    return [min(nums), max(nums)]\n",
    ),
    L(
        slug="lists-rank", title="Leaderboards & ranking", concept=LI, entrypoint="top_scores",
        prompt="Write `top_scores(scores, n)` returning the `n` highest scores, biggest "
               "first.\n\n```python\ntop_scores([40, 10, 90, 50], 2)  # -> [90, 50]\n```",
        starter="def top_scores(scores, n):\n    # Sort high-to-low, then take the first n.\n    return []\n",
        tests=[t("top two", [[40, 10, 90, 50], 2], [90, 50]),
               t("all of them", [[5, 3], 5], [5, 3]),
               t("ties", [[7, 7, 1], 2], [7, 7], hidden=True)],
        hints=_h("Sort with `reverse=True`, then slice `[:n]`.",
                 "`sorted(scores, reverse=True)[:n]`."),
        solution="def top_scores(scores, n):\n    return sorted(scores, reverse=True)[:n]\n",
    ),
    L(
        slug="lists-table", title="Rows of data", concept=LI, entrypoint="column",
        prompt="Rows are lists. Write `column(rows, i)` returning the value at index "
               "`i` from every row.\n\n```python\ncolumn([[1, 2], [3, 4]], 0)  # -> [1, 3]\n```",
        starter="def column(rows, i):\n    result = []\n    # Take item i from each row.\n    return result\n",
        tests=[t("first column", [[[1, 2], [3, 4]], 0], [1, 3]),
               t("second column", [[[1, 2], [3, 4]], 1], [2, 4]),
               t("one row", [[["a", "b"]], 1], ["b"], hidden=True)],
        hints=_h("Loop over rows; take `row[i]` from each.",
                 "`[row[i] for row in rows]`."),
        solution="def column(rows, i):\n    return [row[i] for row in rows]\n",
    ),
    # ===================================================================== LOOPS
    L(
        slug="loops-for", title="Counting with for", concept=LO, entrypoint="sum_to",
        prompt="Write `sum_to(n)` returning 1 + 2 + ... + n using a loop.\n\n"
               "```python\nsum_to(4)  # -> 10\n```",
        starter="def sum_to(n):\n    total = 0\n    # Add each number from 1 to n.\n    return total\n",
        tests=[t("to four", [4], 10), t("to one", [1], 1), t("to zero", [0], 0, hidden=True)],
        hints=_h("`range(1, n + 1)` gives 1..n. Add each to total.",
                 "`for i in range(1, n + 1): total += i`."),
        solution="def sum_to(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n",
    ),
    L(
        slug="loops-range", title="Ranges & steps", concept=LO, entrypoint="evens_below",
        prompt="Write `evens_below(n)` returning a list of the even numbers from 0 up "
               "to (but not including) `n`.\n\n```python\nevens_below(6)  # -> [0, 2, 4]\n```",
        starter="def evens_below(n):\n    # range can step in twos: range(0, n, 2).\n    return []\n",
        tests=[t("below six", [6], [0, 2, 4]), t("below one", [1], [0]),
               t("below zero", [0], [], hidden=True)],
        hints=_h("`range(0, n, 2)` counts 0, 2, 4, ...",
                 "Return `list(range(0, n, 2))`."),
        solution="def evens_below(n):\n    return list(range(0, n, 2))\n",
    ),
    L(
        slug="loops-accum", title="Building up a total", concept=LO, entrypoint="running_total",
        prompt="Write `running_total(nums)` returning a list of the cumulative sums.\n\n"
               "```python\nrunning_total([1, 2, 3])  # -> [1, 3, 6]\n```",
        starter="def running_total(nums):\n    result = []\n    total = 0\n    # Keep a total; append it each step.\n    return result\n",
        tests=[t("basic", [[1, 2, 3]], [1, 3, 6]),
               t("with zero", [[5, 0, 2]], [5, 5, 7]),
               t("empty", [[]], [], hidden=True)],
        hints=_h("Carry `total` across the loop; append it after each add.",
                 "`for n in nums: total += n; result.append(total)`."),
        solution="def running_total(nums):\n    result = []\n    total = 0\n    for n in nums:\n        total += n\n        result.append(total)\n    return result\n",
    ),
    L(
        slug="loops-cond", title="Deciding inside a loop", concept=LO, entrypoint="sum_positives",
        prompt="Write `sum_positives(nums)` returning the total of only the numbers "
               "above 0.\n\n```python\nsum_positives([-2, 3, 4])  # -> 7\n```",
        starter="def sum_positives(nums):\n    total = 0\n    # Only add the positive ones.\n    return total\n",
        tests=[t("mixed", [[-2, 3, 4]], 7), t("all negative", [[-1, -2]], 0),
               t("empty", [[]], 0, hidden=True)],
        hints=_h("Inside the loop, use an if to decide whether to add.",
                 "`for n in nums: if n > 0: total += n`."),
        solution="def sum_positives(nums):\n    total = 0\n    for n in nums:\n        if n > 0:\n            total += n\n    return total\n",
    ),
    L(
        slug="loops-break", title="Stopping early & skipping", concept=LO, entrypoint="first_over",
        prompt="Write `first_over(nums, limit)` returning the first number greater than "
               "`limit`, or -1 if there isn't one. Stop as soon as you find it.\n\n"
               "```python\nfirst_over([1, 5, 8], 4)  # -> 5\n```",
        starter="def first_over(nums, limit):\n    # Loop; return the moment you find one.\n    return -1\n",
        tests=[t("finds it", [[1, 5, 8], 4], 5), t("none over", [[1, 2], 9], -1),
               t("first already over", [[10, 1], 5], 10, hidden=True)],
        hints=_h("Return inside the loop the moment `n > limit` — that stops early.",
                 "`for n in nums: if n > limit: return n` then `return -1`."),
        solution="def first_over(nums, limit):\n    for n in nums:\n        if n > limit:\n            return n\n    return -1\n",
    ),
    L(
        slug="loops-nested", title="Nested loops", concept=LO, entrypoint="all_pairs",
        prompt="Write `all_pairs(a, b)` returning every `[x, y]` pair with x from `a` "
               "and y from `b`.\n\n```python\nall_pairs([1, 2], [3, 4])\n# -> [[1, 3], [1, 4], [2, 3], [2, 4]]\n```",
        starter="def all_pairs(a, b):\n    result = []\n    # A loop inside a loop.\n    return result\n",
        tests=[t("2x2", [[1, 2], [3, 4]], [[1, 3], [1, 4], [2, 3], [2, 4]]),
               t("one each", [[1], [9]], [[1, 9]]),
               t("empty b", [[1, 2], []], [], hidden=True)],
        hints=_h("For each x in a, loop over every y in b.",
                 "`for x in a: for y in b: result.append([x, y])`."),
        solution="def all_pairs(a, b):\n    result = []\n    for x in a:\n        for y in b:\n            result.append([x, y])\n    return result\n",
    ),
    L(
        slug="loops-terminate", title="Making loops end", concept=LO, entrypoint="countdown",
        prompt="Write `countdown(n)` returning `[n, n-1, ..., 1]` using a while loop.\n\n"
               "```python\ncountdown(3)  # -> [3, 2, 1]\n```",
        starter="def countdown(n):\n    result = []\n    # while n > 0: ... make sure n shrinks!\n    return result\n",
        tests=[t("three", [3], [3, 2, 1]), t("one", [1], [1]),
               t("zero", [0], [], hidden=True)],
        hints=_h("Loop while n > 0, append n, then decrease n so it ends.",
                 "`while n > 0: result.append(n); n -= 1`."),
        solution="def countdown(n):\n    result = []\n    while n > 0:\n        result.append(n)\n        n -= 1\n    return result\n",
    ),
    L(
        slug="loops-collect", title="Collecting as you go", concept=LO, entrypoint="squares",
        prompt="Write `squares(n)` returning `[1, 4, 9, ...]` — the squares of 1 to `n`.\n\n"
               "```python\nsquares(3)  # -> [1, 4, 9]\n```",
        starter="def squares(n):\n    result = []\n    # Square each number 1..n.\n    return result\n",
        tests=[t("three", [3], [1, 4, 9]), t("one", [1], [1]),
               t("zero", [0], [], hidden=True)],
        hints=_h("Loop `range(1, n + 1)`; append `i * i`.",
                 "`for i in range(1, n + 1): result.append(i * i)`."),
        solution="def squares(n):\n    return [i * i for i in range(1, n + 1)]\n",
    ),
    L(
        slug="loops-sim", title="Simulating turns", concept=LO, entrypoint="halvings",
        prompt="Write `halvings(n)` returning how many times you can halve `n` (integer "
               "division) before it reaches 0.\n\n```python\nhalvings(8)  # -> 4\n```",
        starter="def halvings(n):\n    count = 0\n    # while n > 0: n = n // 2; count it.\n    return count\n",
        tests=[t("eight", [8], 4), t("one", [1], 1), t("zero", [0], 0, hidden=True)],
        hints=_h("Each turn, do `n = n // 2` and add 1 to count, until n is 0.",
                 "`while n > 0: n = n // 2; count += 1`."),
        solution="def halvings(n):\n    count = 0\n    while n > 0:\n        n = n // 2\n        count += 1\n    return count\n",
    ),
    L(
        slug="loops-scan", title="Searching & scanning", concept=LO, entrypoint="index_of",
        prompt="Write `index_of(items, target)` returning the position of the first "
               "`target`, or -1 if it isn't there.\n\n```python\nindex_of([\"a\", \"b\", \"c\"], \"b\")  # -> 1\n```",
        starter="def index_of(items, target):\n    # Loop with the position; return it when it matches.\n    return -1\n",
        tests=[t("found", [["a", "b", "c"], "b"], 1),
               t("missing", [["a", "b"], "z"], -1),
               t("first", [[5, 5], 5], 0, hidden=True)],
        hints=_h("`for i in range(len(items)):` lets you check `items[i]`.",
                 "Return `i` when `items[i] == target`, else -1 at the end."),
        solution="def index_of(items, target):\n    for i in range(len(items)):\n        if items[i] == target:\n            return i\n    return -1\n",
    ),
    # ============================================================== DICTIONARIES
    L(
        slug="dicts-make", title="Making a dictionary", concept=DI, entrypoint="pair_up",
        prompt="Write `pair_up(keys, values)` returning a dictionary mapping each key to "
               "the value in the same position.\n\n```python\npair_up([\"a\", \"b\"], [1, 2])  # -> {\"a\": 1, \"b\": 2}\n```",
        starter="def pair_up(keys, values):\n    result = {}\n    # Match keys[i] to values[i].\n    return result\n",
        tests=[t("two", [["a", "b"], [1, 2]], {"a": 1, "b": 2}),
               t("one", [["x"], [9]], {"x": 9}),
               t("empty", [[], []], {}, hidden=True)],
        hints=_h("`dict(zip(keys, values))` pairs them up.",
                 "Return `dict(zip(keys, values))`."),
        solution="def pair_up(keys, values):\n    return dict(zip(keys, values))\n",
    ),
    L(
        slug="dicts-get", title="Lookups & .get", concept=DI, entrypoint="safe_get",
        prompt="Write `safe_get(d, key)` returning the value for `key`, or 0 if the key "
               "isn't there.\n\n```python\nsafe_get({\"a\": 5}, \"b\")  # -> 0\n```",
        starter="def safe_get(d, key):\n    # d.get(key, fallback) never crashes.\n    return 0\n",
        tests=[t("present", [{"a": 5}, "a"], 5), t("missing", [{"a": 5}, "b"], 0),
               t("empty dict", [{}, "x"], 0, hidden=True)],
        hints=_h("`d.get(key)` returns None if missing; pass a default.",
                 "Return `d.get(key, 0)`."),
        solution="def safe_get(d, key):\n    return d.get(key, 0)\n",
    ),
    L(
        slug="dicts-update", title="Adding & updating", concept=DI, entrypoint="add_points",
        prompt="Write `add_points(scores, name, n)` that adds `n` to `name`'s score "
               "(starting from 0 if new) and returns the updated dictionary.\n\n"
               "```python\nadd_points({\"ana\": 2}, \"ana\", 3)  # -> {\"ana\": 5}\n```",
        starter="def add_points(scores, name, n):\n    # Use .get to start missing names at 0.\n    return scores\n",
        tests=[t("existing", [{"ana": 2}, "ana", 3], {"ana": 5}),
               t("new name", [{"ana": 2}, "bo", 4], {"ana": 2, "bo": 4}),
               t("from empty", [{}, "x", 1], {"x": 1}, hidden=True)],
        hints=_h("`scores.get(name, 0)` gives the current score or 0.",
                 "`scores[name] = scores.get(name, 0) + n` then return scores."),
        solution="def add_points(scores, name, n):\n    scores[name] = scores.get(name, 0) + n\n    return scores\n",
    ),
    L(
        slug="dicts-iter", title="Looping over a dict", concept=DI, entrypoint="total_values",
        prompt="Write `total_values(d)` returning the sum of all the values.\n\n"
               "```python\ntotal_values({\"a\": 2, \"b\": 3})  # -> 5\n```",
        starter="def total_values(d):\n    total = 0\n    # Loop over the values.\n    return total\n",
        tests=[t("two", [{"a": 2, "b": 3}], 5), t("one", [{"x": 9}], 9),
               t("empty", [{}], 0, hidden=True)],
        hints=_h("`d.values()` gives you the values to add up.",
                 "`for v in d.values(): total += v`, or `sum(d.values())`."),
        solution="def total_values(d):\n    return sum(d.values())\n",
    ),
    L(
        slug="dicts-count", title="Counting things", concept=DI, entrypoint="count_items",
        prompt="Write `count_items(items)` returning a dictionary of how many times each "
               "item appears.\n\n```python\ncount_items([\"a\", \"b\", \"a\"])  # -> {\"a\": 2, \"b\": 1}\n```",
        starter="def count_items(items):\n    counts = {}\n    # Tally each item.\n    return counts\n",
        tests=[t("repeats", [["a", "b", "a"]], {"a": 2, "b": 1}),
               t("all unique", [["x", "y"]], {"x": 1, "y": 1}),
               t("empty", [[]], {}, hidden=True)],
        hints=_h("For each item, add 1 to its count, starting from 0 if new.",
                 "`counts[item] = counts.get(item, 0) + 1`."),
        solution="def count_items(items):\n    counts = {}\n    for item in items:\n        counts[item] = counts.get(item, 0) + 1\n    return counts\n",
    ),
    L(
        slug="dicts-group", title="Grouping items", concept=DI, entrypoint="group_by_first",
        prompt="Write `group_by_first(words)` returning a dictionary from each starting "
               "letter to the list of words that begin with it, in order.\n\n"
               "```python\ngroup_by_first([\"ant\", \"bee\", \"ape\"])  # -> {\"a\": [\"ant\", \"ape\"], \"b\": [\"bee\"]}\n```",
        starter="def group_by_first(words):\n    groups = {}\n    # Bucket each word by its first letter.\n    return groups\n",
        tests=[t("mixed", [["ant", "bee", "ape"]], {"a": ["ant", "ape"], "b": ["bee"]}),
               t("all same", [["cat", "cow"]], {"c": ["cat", "cow"]}),
               t("empty", [[]], {}, hidden=True)],
        hints=_h("Use `setdefault(word[0], [])` then append the word.",
                 "`groups.setdefault(w[0], []).append(w)`."),
        solution="def group_by_first(words):\n    groups = {}\n    for w in words:\n        groups.setdefault(w[0], []).append(w)\n    return groups\n",
    ),
    L(
        slug="dicts-comp", title="Dict comprehensions", concept=DI, entrypoint="lengths",
        prompt="Write `lengths(words)` returning a dictionary from each word to its "
               "length. Try a dict comprehension.\n\n"
               "```python\nlengths([\"hi\", \"cat\"])  # -> {\"hi\": 2, \"cat\": 3}\n```",
        starter="def lengths(words):\n    # {word: len(word) for word in words}\n    return {}\n",
        tests=[t("basic", [["hi", "cat"]], {"hi": 2, "cat": 3}),
               t("one", [["x"]], {"x": 1}),
               t("empty", [[]], {}, hidden=True)],
        hints=_h("A dict comprehension: `{k: v for ...}`.",
                 "`{w: len(w) for w in words}`."),
        solution="def lengths(words):\n    return {w: len(w) for w in words}\n",
    ),
    L(
        slug="dicts-nested", title="Nested dictionaries", concept=DI, entrypoint="get_nested",
        prompt="Write `get_nested(d, outer, inner)` returning `d[outer][inner]`.\n\n"
               "```python\nget_nested({\"a\": {\"x\": 1}}, \"a\", \"x\")  # -> 1\n```",
        starter="def get_nested(d, outer, inner):\n    # Reach in twice.\n    return None\n",
        tests=[t("basic", [{"a": {"x": 1}}, "a", "x"], 1),
               t("other key", [{"a": {"x": 1, "y": 2}}, "a", "y"], 2),
               t("deep", [{"p": {"q": 9}}, "p", "q"], 9, hidden=True)],
        hints=_h("`d[outer]` is itself a dictionary; index it again.",
                 "Return `d[outer][inner]`."),
        solution="def get_nested(d, outer, inner):\n    return d[outer][inner]\n",
    ),
    L(
        slug="dicts-default", title="Defaults & Counter", concept=DI, entrypoint="merge_counts",
        prompt="Write `merge_counts(a, b)` returning a dictionary that adds together the "
               "counts from two dictionaries.\n\n"
               "```python\nmerge_counts({\"x\": 1}, {\"x\": 2, \"y\": 1})  # -> {\"x\": 3, \"y\": 1}\n```",
        starter="def merge_counts(a, b):\n    result = dict(a)\n    # Add each of b's counts on top.\n    return result\n",
        tests=[t("overlap", [{"x": 1}, {"x": 2, "y": 1}], {"x": 3, "y": 1}),
               t("no overlap", [{"a": 1}, {"b": 2}], {"a": 1, "b": 2}),
               t("empty b", [{"a": 5}, {}], {"a": 5}, hidden=True)],
        hints=_h("Start from a copy of a; for each key in b, add its value.",
                 "`result[k] = result.get(k, 0) + v` for k, v in b.items()."),
        solution="def merge_counts(a, b):\n    result = dict(a)\n    for k, v in b.items():\n        result[k] = result.get(k, 0) + v\n    return result\n",
    ),
    L(
        slug="dicts-inventory", title="Inventories & records", concept=DI, entrypoint="total_cost",
        prompt="`prices` maps item to price; `cart` maps item to quantity. Write "
               "`total_cost(prices, cart)` returning the total.\n\n"
               "```python\ntotal_cost({\"apple\": 2, \"pear\": 3}, {\"apple\": 4})  # -> 8\n```",
        starter="def total_cost(prices, cart):\n    total = 0\n    # price of each item times its quantity.\n    return total\n",
        tests=[t("one item", [{"apple": 2, "pear": 3}, {"apple": 4}], 8),
               t("two items", [{"a": 1, "b": 5}, {"a": 2, "b": 1}], 7),
               t("empty cart", [{"a": 9}, {}], 0, hidden=True)],
        hints=_h("Loop over the cart; multiply price by quantity.",
                 "`for item, qty in cart.items(): total += prices[item] * qty`."),
        solution="def total_cost(prices, cart):\n    total = 0\n    for item, qty in cart.items():\n        total += prices[item] * qty\n    return total\n",
    ),
    L(
        slug="dicts-freq", title="Word frequency", concept=DI, entrypoint="most_common",
        prompt="Write `most_common(words)` returning the word that appears most often. "
               "On a tie, return the one that appears first.\n\n"
               "```python\nmost_common([\"a\", \"b\", \"a\"])  # -> \"a\"\n```",
        starter="def most_common(words):\n    counts = {}\n    # Tally, then find the biggest.\n    return None\n",
        tests=[t("clear winner", [["a", "b", "a"]], "a"),
               t("tie keeps first", [["x", "y"]], "x"),
               t("single", [["z"]], "z", hidden=True)],
        hints=_h("Count them first, then walk the words tracking the best count.",
                 "Tally into counts, then loop words keeping the max; first-seen wins ties."),
        solution="def most_common(words):\n    counts = {}\n    for w in words:\n        counts[w] = counts.get(w, 0) + 1\n    best = None\n    best_n = -1\n    for w in words:\n        if counts[w] > best_n:\n            best = w\n            best_n = counts[w]\n    return best\n",
    ),
    # =================================================================== STRINGS
    L(
        slug="str-index", title="Indexing & slicing text", concept=ST, entrypoint="initials",
        prompt="Write `initials(first, last)` returning the two first letters joined, "
               "uppercase.\n\n```python\ninitials(\"ada\", \"lovelace\")  # -> \"AL\"\n```",
        starter="def initials(first, last):\n    # first[0] is the first letter.\n    return \"\"\n",
        tests=[t("basic", ["ada", "lovelace"], "AL"),
               t("already caps", ["Bo", "Xu"], "BX"),
               t("single letters", ["a", "b"], "AB", hidden=True)],
        hints=_h("`first[0]` and `last[0]` are the first letters; `.upper()` capitalises.",
                 "Return `(first[0] + last[0]).upper()`."),
        solution="def initials(first, last):\n    return (first[0] + last[0]).upper()\n",
    ),
    L(
        slug="str-case", title="Case & tidying up", concept=ST, entrypoint="shout",
        prompt="Write `shout(s)` returning the text in upper case with surrounding "
               "spaces removed.\n\n```python\nshout(\"  hi  \")  # -> \"HI\"\n```",
        starter="def shout(s):\n    # .strip() trims spaces, .upper() shouts.\n    return s\n",
        tests=[t("spaces", ["  hi  "], "HI"), t("already", ["ok"], "OK"),
               t("empty", ["   "], "", hidden=True)],
        hints=_h("Chain the two: strip first, then upper.",
                 "Return `s.strip().upper()`."),
        solution="def shout(s):\n    return s.strip().upper()\n",
    ),
    L(
        slug="str-fstring", title="Joining text & f-strings", concept=ST, entrypoint="greet",
        prompt="Write `greet(name, count)` returning `\"Hello NAME, you have COUNT "
               "messages\"`.\n\n```python\ngreet(\"Ada\", 3)  # -> \"Hello Ada, you have 3 messages\"\n```",
        starter="def greet(name, count):\n    # An f-string slots values into text.\n    return \"\"\n",
        tests=[t("basic", ["Ada", 3], "Hello Ada, you have 3 messages"),
               t("zero", ["Bo", 0], "Hello Bo, you have 0 messages"),
               t("one", ["X", 1], "Hello X, you have 1 messages", hidden=True)],
        hints=_h("`f\"Hello {name}...\"` drops values straight in.",
                 "Return `f\"Hello {name}, you have {count} messages\"`."),
        solution="def greet(name, count):\n    return f\"Hello {name}, you have {count} messages\"\n",
    ),
    L(
        slug="str-split", title="Splitting & joining", concept=ST, entrypoint="word_count",
        prompt="Write `word_count(s)` returning how many words are in the text (split on "
               "spaces).\n\n```python\nword_count(\"the quick fox\")  # -> 3\n```",
        starter="def word_count(s):\n    # .split() breaks on whitespace into a list.\n    return 0\n",
        tests=[t("three", ["the quick fox"], 3), t("one", ["hello"], 1),
               t("empty", [""], 0, hidden=True)],
        hints=_h("`s.split()` returns the words; `len(...)` counts them.",
                 "Return `len(s.split())`."),
        solution="def word_count(s):\n    return len(s.split())\n",
    ),
    L(
        slug="str-search", title="Searching & replacing", concept=ST, entrypoint="count_char",
        prompt="Write `count_char(s, c)` returning how many times character `c` appears "
               "in `s`.\n\n```python\ncount_char(\"banana\", \"a\")  # -> 3\n```",
        starter="def count_char(s, c):\n    # Strings have a .count method.\n    return 0\n",
        tests=[t("three a", ["banana", "a"], 3), t("none", ["banana", "z"], 0),
               t("all same", ["aaa", "a"], 3, hidden=True)],
        hints=_h("`s.count(c)` counts occurrences.",
                 "Return `s.count(c)`."),
        solution="def count_char(s, c):\n    return s.count(c)\n",
    ),
    L(
        slug="str-format", title="Formatting & alignment", concept=ST, entrypoint="pad_id",
        prompt="Write `pad_id(n, width)` returning `n` as text, padded with leading "
               "zeros to `width` characters.\n\n```python\npad_id(42, 5)  # -> \"00042\"\n```",
        starter="def pad_id(n, width):\n    # str(n).zfill(width) pads with zeros.\n    return \"\"\n",
        tests=[t("pad", [42, 5], "00042"), t("exact", [12345, 5], "12345"),
               t("single", [7, 3], "007", hidden=True)],
        hints=_h("Turn n into text, then zero-fill it.",
                 "Return `str(n).zfill(width)`."),
        solution="def pad_id(n, width):\n    return str(n).zfill(width)\n",
    ),
    L(
        slug="str-validate", title="Checking input is valid", concept=ST, entrypoint="is_whole_number",
        prompt="Write `is_whole_number(s)` returning True if the text is a whole number "
               "(digits only, optional leading minus), else False.\n\n"
               "```python\nis_whole_number(\"42\")  # -> True\nis_whole_number(\"4a\")  # -> False\n```",
        starter="def is_whole_number(s):\n    # Try turning it into an int.\n    return False\n",
        tests=[t("digits", ["42"], True), t("negative", ["-7"], True),
               t("letters", ["4a"], False), t("empty", [""], False, hidden=True)],
        hints=_h("`int(s)` raises if it isn't a whole number — catch that.",
                 "try: `int(s)`; return True; except: return False."),
        solution="def is_whole_number(s):\n    try:\n        int(s)\n        return True\n    except ValueError:\n        return False\n",
    ),
    L(
        slug="str-build", title="Building text from data", concept=ST, entrypoint="bullet_list",
        prompt="Write `bullet_list(items)` returning the items as bullet lines joined by "
               "newlines: `\"- a\\n- b\"`.\n\n```python\nbullet_list([\"a\", \"b\"])  # -> \"- a\\n- b\"\n```",
        starter="def bullet_list(items):\n    # Build \"- item\" for each, join with newlines.\n    return \"\"\n",
        tests=[t("two", [["a", "b"]], "- a\n- b"), t("one", [["x"]], "- x"),
               t("empty", [[]], "", hidden=True)],
        hints=_h("Make a list of `\"- \" + item`, then `\"\\n\".join(...)`.",
                 "`\"\\n\".join(\"- \" + i for i in items)`."),
        solution="def bullet_list(items):\n    return \"\\n\".join(\"- \" + i for i in items)\n",
    ),
    L(
        slug="str-csv", title="Reading line-based data", concept=ST, entrypoint="parse_row",
        prompt="Write `parse_row(line)` returning the comma-separated fields as a list, "
               "with surrounding spaces trimmed.\n\n"
               "```python\nparse_row(\"ada, 42, uk\")  # -> [\"ada\", \"42\", \"uk\"]\n```",
        starter="def parse_row(line):\n    # Split on commas, strip each field.\n    return []\n",
        tests=[t("basic", ["ada, 42, uk"], ["ada", "42", "uk"]),
               t("no spaces", ["a,b"], ["a", "b"]),
               t("single", ["only"], ["only"], hidden=True)],
        hints=_h("`line.split(\",\")` gives fields; strip each one.",
                 "`[field.strip() for field in line.split(\",\")]`."),
        solution="def parse_row(line):\n    return [field.strip() for field in line.split(\",\")]\n",
    ),
    L(
        slug="str-report", title="Generating a report", concept=ST, entrypoint="scoreline",
        prompt="Write `scoreline(name, score)` returning `\"NAME scored SCORE\"`, but "
               "`\"NAME scored 0 — try again!\"` when the score is 0.\n\n"
               "```python\nscoreline(\"Bo\", 5)  # -> \"Bo scored 5\"\n```",
        starter="def scoreline(name, score):\n    # Two cases: zero and non-zero.\n    return \"\"\n",
        tests=[t("normal", ["Bo", 5], "Bo scored 5"),
               t("zero", ["Ana", 0], "Ana scored 0 — try again!"),
               t("one", ["X", 1], "X scored 1", hidden=True)],
        hints=_h("An if decides which sentence to build.",
                 "if score == 0: return the try-again line; else the plain one."),
        solution="def scoreline(name, score):\n    if score == 0:\n        return f\"{name} scored 0 — try again!\"\n    return f\"{name} scored {score}\"\n",
    ),
    # ================================================================= FUNCTIONS
    L(
        slug="fn-define", title="Defining & calling", concept=FN, entrypoint="greeting",
        prompt="Write `greeting()` — no arguments — that returns the text `\"Hello!\"`.\n\n"
               "```python\ngreeting()  # -> \"Hello!\"\n```",
        starter="def greeting():\n    # Return the greeting.\n    return \"\"\n",
        tests=[t("says hello", [], "Hello!")],
        hints=_h("A function with no inputs still returns a value.",
                 "Return the string `\"Hello!\"`."),
        solution="def greeting():\n    return \"Hello!\"\n",
    ),
    L(
        slug="fn-params", title="Parameters & return", concept=FN, entrypoint="area",
        prompt="Write `area(width, height)` returning the rectangle's area.\n\n"
               "```python\narea(3, 4)  # -> 12\n```",
        starter="def area(width, height):\n    # Multiply the two.\n    return 0\n",
        tests=[t("basic", [3, 4], 12), t("square", [5, 5], 25),
               t("zero", [0, 9], 0, hidden=True)],
        hints=_h("Area is width times height.",
                 "Return `width * height`."),
        solution="def area(width, height):\n    return width * height\n",
    ),
    L(
        slug="fn-defaults", title="Default arguments", concept=FN, entrypoint="hello",
        prompt="Write `hello(name=\"friend\")` returning `\"Hi, NAME\"`. Called with no "
               "name it should greet `\"friend\"`.\n\n"
               "```python\nhello()  # -> \"Hi, friend\"\nhello(\"Ada\")  # -> \"Hi, Ada\"\n```",
        starter="def hello(name=\"friend\"):\n    # Use the name, whatever it is.\n    return \"\"\n",
        tests=[t("given", ["Ada"], "Hi, Ada"), t("default", [], "Hi, friend"),
               t("other", ["Bo"], "Hi, Bo", hidden=True)],
        hints=_h("The default in the signature handles the no-argument call.",
                 "Return `f\"Hi, {name}\"`."),
        solution="def hello(name=\"friend\"):\n    return f\"Hi, {name}\"\n",
    ),
    L(
        slug="fn-decompose", title="Breaking a problem down", concept=FN, entrypoint="price_with_tax",
        prompt="Write `price_with_tax(price, rate)` returning the price plus tax, where "
               "`rate` is a percentage.\n\n```python\nprice_with_tax(100, 20)  # -> 120.0\n```",
        starter="def price_with_tax(price, rate):\n    # Add rate percent of price.\n    return 0\n",
        tests=[t("twenty percent", [100, 20], 120.0),
               t("no tax", [50, 0], 50.0),
               t("ten percent", [200, 10], 220.0, hidden=True)],
        hints=_h("The tax is `price * rate / 100`.",
                 "Return `price + price * rate / 100`."),
        solution="def price_with_tax(price, rate):\n    return price + price * rate / 100\n",
    ),
    L(
        slug="fn-pure", title="Pure functions & side effects", concept=FN, entrypoint="discounted",
        prompt="Write `discounted(price, pct)` returning the price after taking `pct` "
               "percent off. Don't change anything else.\n\n"
               "```python\ndiscounted(100, 25)  # -> 75.0\n```",
        starter="def discounted(price, pct):\n    # Return the new price; change nothing outside.\n    return 0\n",
        tests=[t("quarter off", [100, 25], 75.0), t("nothing off", [40, 0], 40.0),
               t("half off", [10, 50], 5.0, hidden=True)],
        hints=_h("Keep `pct` percent of the price: multiply by (100 - pct)/100.",
                 "Return `price * (100 - pct) / 100`."),
        solution="def discounted(price, pct):\n    return price * (100 - pct) / 100\n",
    ),
    L(
        slug="fn-recursion", title="Recursion", concept=FN, entrypoint="factorial",
        prompt="Write `factorial(n)` returning n! = n × (n-1) × ... × 1, with "
               "`factorial(0)` = 1. Have the function call itself.\n\n"
               "```python\nfactorial(4)  # -> 24\n```",
        starter="def factorial(n):\n    # Base case: 0 -> 1. Otherwise n * factorial(n-1).\n    return 1\n",
        tests=[t("four", [4], 24), t("zero", [0], 1), t("one", [1], 1, hidden=True)],
        hints=_h("Stop at 0 (return 1); otherwise multiply n by factorial(n-1).",
                 "if n == 0: return 1; else return n * factorial(n - 1)."),
        solution="def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n - 1)\n",
    ),
    L(
        slug="fn-higher", title="Passing functions around", concept=FN, entrypoint="keep_positive",
        prompt="Write `keep_positive(nums)` returning only the numbers above 0, using "
               "`filter` (or a comprehension).\n\n"
               "```python\nkeep_positive([-1, 2, -3, 4])  # -> [2, 4]\n```",
        starter="def keep_positive(nums):\n    # filter(lambda n: n > 0, nums)\n    return []\n",
        tests=[t("mixed", [[-1, 2, -3, 4]], [2, 4]), t("all positive", [[1, 2]], [1, 2]),
               t("none", [[-1, -2]], [], hidden=True)],
        hints=_h("`filter(fn, nums)` keeps items where fn returns True.",
                 "`list(filter(lambda n: n > 0, nums))`."),
        solution="def keep_positive(nums):\n    return list(filter(lambda n: n > 0, nums))\n",
    ),
    L(
        slug="fn-lambda", title="Lambdas", concept=FN, entrypoint="by_length",
        prompt="Write `by_length(words)` returning the words sorted shortest first, using "
               "a `key`.\n\n```python\nby_length([\"ccc\", \"a\", \"bb\"])  # -> [\"a\", \"bb\", \"ccc\"]\n```",
        starter="def by_length(words):\n    # sorted(words, key=len)\n    return []\n",
        tests=[t("basic", [["ccc", "a", "bb"]], ["a", "bb", "ccc"]),
               t("already", [["a", "bb"]], ["a", "bb"]),
               t("one", [["x"]], ["x"], hidden=True)],
        hints=_h("`sorted(words, key=len)` orders by length.",
                 "Return `sorted(words, key=len)`."),
        solution="def by_length(words):\n    return sorted(words, key=len)\n",
    ),
    L(
        slug="fn-library", title="Building a small toolkit", concept=FN, entrypoint="normalize",
        prompt="Write `normalize(s)` returning the text trimmed of spaces and lower-cased "
               "— the kind of tidy-up helper you'd reuse everywhere.\n\n"
               "```python\nnormalize(\"  HeLLo \")  # -> \"hello\"\n```",
        starter="def normalize(s):\n    # strip then lower.\n    return s\n",
        tests=[t("messy", ["  HeLLo "], "hello"), t("clean", ["ok"], "ok"),
               t("spaces only", ["   "], "", hidden=True)],
        hints=_h("Chain `.strip()` and `.lower()`.",
                 "Return `s.strip().lower()`."),
        solution="def normalize(s):\n    return s.strip().lower()\n",
    ),
    L(
        slug="fn-test", title="Testing your own functions", concept=FN, entrypoint="is_palindrome",
        prompt="Write `is_palindrome(s)` returning True if the text reads the same "
               "forwards and backwards.\n\n```python\nis_palindrome(\"level\")  # -> True\n```",
        starter="def is_palindrome(s):\n    # s[::-1] is s reversed.\n    return False\n",
        tests=[t("palindrome", ["level"], True), t("not", ["hello"], False),
               t("single", ["a"], True, hidden=True)],
        hints=_h("`s[::-1]` reverses the string; compare it to `s`.",
                 "Return `s == s[::-1]`."),
        solution="def is_palindrome(s):\n    return s == s[::-1]\n",
    ),
    # ===================================================================== FILES
    L(
        slug="file-read", title="Reading a file's contents", concept=FI, entrypoint="char_count",
        prompt="You get a file's whole contents as a string. Write `char_count(contents)` "
               "returning how many characters it has.\n\n"
               "```python\nchar_count(\"abc\")  # -> 3\n```",
        starter="def char_count(contents):\n    # len() counts characters.\n    return 0\n",
        tests=[t("three", ["abc"], 3), t("with newline", ["a\nb"], 3),
               t("empty", [""], 0, hidden=True)],
        hints=_h("`len(contents)` is the character count.",
                 "Return `len(contents)`."),
        solution="def char_count(contents):\n    return len(contents)\n",
    ),
    L(
        slug="file-lines", title="Lines vs whole text", concept=FI, entrypoint="line_count",
        prompt="Write `line_count(contents)` returning how many lines the file has.\n\n"
               "```python\nline_count(\"a\\nb\\nc\")  # -> 3\n```",
        starter="def line_count(contents):\n    # splitlines() breaks text into lines.\n    return 0\n",
        tests=[t("three", ["a\nb\nc"], 3), t("one", ["hello"], 1),
               t("empty", [""], 0, hidden=True)],
        hints=_h("`contents.splitlines()` gives a list of lines.",
                 "Return `len(contents.splitlines())`."),
        solution="def line_count(contents):\n    return len(contents.splitlines())\n",
    ),
    L(
        slug="file-trailing", title="Coping with blank lines", concept=FI, entrypoint="real_lines",
        prompt="Write `real_lines(contents)` returning the non-blank lines as a list "
               "(ignore lines that are empty or only spaces).\n\n"
               "```python\nreal_lines(\"a\\n\\nb\\n\")  # -> [\"a\", \"b\"]\n```",
        starter="def real_lines(contents):\n    result = []\n    # Skip lines that are blank after stripping.\n    return result\n",
        tests=[t("trailing", ["a\n\nb\n"], ["a", "b"]),
               t("spaces line", ["x\n   \ny"], ["x", "y"]),
               t("all blank", ["\n\n"], [], hidden=True)],
        hints=_h("Loop the split lines; keep ones where `.strip()` isn't empty.",
                 "`[l for l in contents.split('\\n') if l.strip()]`."),
        solution="def real_lines(contents):\n    return [l for l in contents.split(\"\\n\") if l.strip()]\n",
    ),
    L(
        slug="file-summarise", title="Filtering & summarising", concept=FI, entrypoint="sum_lines",
        prompt="Each non-blank line is a number. Write `sum_lines(contents)` returning "
               "their total.\n\n```python\nsum_lines(\"1\\n2\\n3\")  # -> 6\n```",
        starter="def sum_lines(contents):\n    total = 0\n    # int() each non-blank line.\n    return total\n",
        tests=[t("basic", ["1\n2\n3"], 6), t("trailing newline", ["10\n5\n"], 15),
               t("one", ["42"], 42, hidden=True)],
        hints=_h("Skip blank lines; add `int(line)` for the rest.",
                 "`for line in contents.split('\\n'): if line.strip(): total += int(line)`."),
        solution="def sum_lines(contents):\n    total = 0\n    for line in contents.split(\"\\n\"):\n        if line.strip():\n            total += int(line)\n    return total\n",
    ),
    L(
        slug="file-write", title="Writing output", concept=FI, entrypoint="to_lines",
        prompt="Write `to_lines(items)` returning the items joined into one string, one "
               "per line.\n\n```python\nto_lines([\"a\", \"b\"])  # -> \"a\\nb\"\n```",
        starter="def to_lines(items):\n    # join with newlines.\n    return \"\"\n",
        tests=[t("two", [["a", "b"]], "a\nb"), t("one", [["x"]], "x"),
               t("empty", [[]], "", hidden=True)],
        hints=_h("`\"\\n\".join(items)` stitches them with newlines.",
                 "Return `\"\\n\".join(items)`."),
        solution="def to_lines(items):\n    return \"\\n\".join(items)\n",
    ),
    L(
        slug="file-csv", title="CSV handling", concept=FI, entrypoint="parse_csv",
        prompt="Write `parse_csv(contents)` returning a list of rows, each row a list of "
               "comma-separated fields. Skip blank lines.\n\n"
               "```python\nparse_csv(\"a,b\\nc,d\")  # -> [[\"a\", \"b\"], [\"c\", \"d\"]]\n```",
        starter="def parse_csv(contents):\n    rows = []\n    # Split into lines, each line on commas.\n    return rows\n",
        tests=[t("two rows", ["a,b\nc,d"], [["a", "b"], ["c", "d"]]),
               t("trailing", ["1,2\n"], [["1", "2"]]),
               t("empty", [""], [], hidden=True)],
        hints=_h("For each non-blank line, `line.split(',')`.",
                 "`[line.split(',') for line in contents.split('\\n') if line.strip()]`."),
        solution="def parse_csv(contents):\n    return [line.split(\",\") for line in contents.split(\"\\n\") if line.strip()]\n",
    ),
    L(
        slug="file-records", title="Lines into records", concept=FI, entrypoint="to_records",
        prompt="The first line is a header of field names; each later line is a row. Write "
               "`to_records(contents)` returning a list of dictionaries.\n\n"
               "```python\nto_records(\"name,age\\nada,42\")  # -> [{\"name\": \"ada\", \"age\": \"42\"}]\n```",
        starter="def to_records(contents):\n    lines = [l for l in contents.split(\"\\n\") if l.strip()]\n    # First line = header; zip it with each row.\n    return []\n",
        tests=[t("one row", ["name,age\nada,42"], [{"name": "ada", "age": "42"}]),
               t("two rows", ["a,b\n1,2\n3,4"], [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]),
               t("header only", ["name,age"], [], hidden=True)],
        hints=_h("Split header on commas; for each remaining line, zip header with its fields.",
                 "`dict(zip(header, line.split(',')))` for each row line."),
        solution="def to_records(contents):\n    lines = [l for l in contents.split(\"\\n\") if l.strip()]\n    if not lines:\n        return []\n    header = lines[0].split(\",\")\n    return [dict(zip(header, line.split(\",\"))) for line in lines[1:]]\n",
    ),
    L(
        slug="file-robust", title="Handling bad data", concept=FI, entrypoint="sum_valid",
        prompt="Each line should be a number, but some are junk. Write "
               "`sum_valid(contents)` returning the total of just the lines that are "
               "whole numbers.\n\n```python\nsum_valid(\"1\\noops\\n3\")  # -> 4\n```",
        starter="def sum_valid(contents):\n    total = 0\n    # Try int() each line; skip the ones that fail.\n    return total\n",
        tests=[t("skips junk", ["1\noops\n3"], 4),
               t("all good", ["2\n2\n2"], 6),
               t("all junk", ["a\nb"], 0, hidden=True)],
        hints=_h("Wrap `int(line)` in try/except and skip failures.",
                 "try: total += int(line) except ValueError: continue."),
        solution="def sum_valid(contents):\n    total = 0\n    for line in contents.split(\"\\n\"):\n        try:\n            total += int(line)\n        except ValueError:\n            continue\n    return total\n",
    ),
    L(
        slug="file-log", title="Log analysis", concept=FI, entrypoint="count_errors",
        prompt="Write `count_errors(contents)` returning how many lines contain the word "
               "`ERROR`.\n\n```python\ncount_errors(\"OK\\nERROR here\\nERROR\")  # -> 2\n```",
        starter="def count_errors(contents):\n    count = 0\n    # Count lines containing 'ERROR'.\n    return count\n",
        tests=[t("two", ["OK\nERROR here\nERROR"], 2), t("none", ["OK\nfine"], 0),
               t("empty", [""], 0, hidden=True)],
        hints=_h("`\"ERROR\" in line` is True when the line contains it.",
                 "Loop lines; `if \"ERROR\" in line: count += 1`."),
        solution="def count_errors(contents):\n    count = 0\n    for line in contents.split(\"\\n\"):\n        if \"ERROR\" in line:\n            count += 1\n    return count\n",
    ),
    L(
        slug="file-pipeline", title="A small data pipeline", concept=FI, entrypoint="top_name",
        prompt="Each line is `name,score`. Write `top_name(contents)` returning the name "
               "with the highest score. Read, parse, then find the max.\n\n"
               "```python\ntop_name(\"ana,10\\nbo,30\\ncy,20\")  # -> \"bo\"\n```",
        starter="def top_name(contents):\n    best = None\n    best_score = -1\n    # Parse each line; track the highest score's name.\n    return best\n",
        tests=[t("middle wins", ["ana,10\nbo,30\ncy,20"], "bo"),
               t("first wins", ["x,99\ny,1"], "x"),
               t("single", ["solo,5"], "solo", hidden=True)],
        hints=_h("Split each line on the comma; compare int(score) to the best so far.",
                 "For each line: name, score = line.split(','); if int(score) > best_score: update."),
        solution="def top_name(contents):\n    best = None\n    best_score = -1\n    for line in contents.split(\"\\n\"):\n        if not line.strip():\n            continue\n        name, score = line.split(\",\")\n        if int(score) > best_score:\n            best = name\n            best_score = int(score)\n    return best\n",
    ),
]
