"""Games & quests -- records with state.

Data shape: things that have happened or haven't, with numbers attached.
Naturally teaches filtering, counting, min/max, and boolean conditions.
"""

from ..models import Concept, Theme
from ._shared import ex, t

TH = Theme.GAMES

GAMES = [
    # ---------------------------------------------------------------- lists
    ex(
        slug="expired-quests",
        title="The quest log",
        theme=TH,
        concept=Concept.LISTS,
        pair_id="pair-lists",
        entrypoint="expired_quests",
        order=1,
        prompt="""\
Every RPG has a quest log, and every quest log has that one job you meant to do
forty hours ago. You're building the bit that finds them.

Each quest is a **name**, the **day it expires**, and whether you've **done** it:

```python
{"name": "Slay the dragon", "due_day": 10, "done": False}
```

`today` is just a number — day 15, say.

Write `expired_quests(quests, today)`. It returns a **list of the names** of the
quests you never finished and whose day has already gone, in log order.

A quest expiring *today* hasn't expired yet. You've still got today.

```python
expired_quests(quests, 15)   # -> ["Slay the dragon"]
```
""",
        starter='''\
def expired_quests(quests, today):
    """Return the names of quests that aren't done and are past their day."""
    expired = []
    # Go through each quest and decide whether it belongs in the list.
    return expired
''',
        tests=[
            t("one expired, one still live",
              [[{"name": "Slay the dragon", "due_day": 10, "done": False},
                {"name": "Find the lost sword", "due_day": 30, "done": False}], 15],
              ["Slay the dragon"]),
            t("completed quests never expire",
              [[{"name": "Slay the dragon", "due_day": 10, "done": True},
                {"name": "Rescue the baker", "due_day": 5, "done": False}], 15],
              ["Rescue the baker"]),
            t("nothing expired yet",
              [[{"name": "Slay the dragon", "due_day": 10, "done": False}], 5], []),
            t("expiring today has not expired yet",
              [[{"name": "Slay the dragon", "due_day": 10, "done": False}], 10], [], hidden=True),
            t("an empty quest log", [[], 20], [], hidden=True),
        ],
        hints={
            "2": ("Look at the loop. For each quest you need to check *two* things "
                  "before adding it: has the day gone, and is it still not done? "
                  "Right now `expired` is being returned exactly as it started."),
            "3": ("Filtering a list means: start with an empty list, look at every "
                  "item, and append only the ones that pass your test. Your test "
                  "here is a quest whose `due_day` is *before* today AND whose "
                  "`done` is False. You want the quest's name in the result, not "
                  "the whole quest."),
            "4": ("The shape is:\n\n"
                  "    make an empty list\n"
                  "    for each quest in quests:\n"
                  "        if the quest's due_day is less than today:\n"
                  "            if the quest is not done:\n"
                  "                add the quest's name to your list\n"
                  "    return the list\n\n"
                  "You get at a quest's name with quest['name']."),
        },
    ),
    # ---------------------------------------------------------------- dicts
    ex(
        slug="can-i-craft-it",
        title="Can I craft it?",
        theme=TH,
        concept=Concept.DICTS,
        entrypoint="can_craft",
        order=2,
        prompt="""\
You've found a recipe. The question every crafting screen has to answer: do you
actually have the stuff?

Your **inventory** and the **recipe** are both dictionaries of item → how many:

```python
inventory = {"iron": 4, "wood": 10, "leather": 1}
recipe    = {"iron": 2, "wood": 3}
```

Write `can_craft(inventory, recipe)` returning `True` or `False`.

You need **at least** the amount the recipe asks for, of every item it lists.
Having spare is fine. Missing an item entirely counts as having none of it.
""",
        starter='''\
def can_craft(inventory, recipe):
    """Return True if the inventory covers every item in the recipe."""
    # Check each item the recipe needs.
    return False
''',
        tests=[
            t("enough of everything", [{"iron": 4, "wood": 10}, {"iron": 2, "wood": 3}], True),
            t("not enough wood", [{"iron": 4, "wood": 1}, {"iron": 2, "wood": 3}], False),
            t("missing the item completely", [{"wood": 10}, {"iron": 1}], False),
            t("exactly enough counts", [{"iron": 2}, {"iron": 2}], True, hidden=True),
            t("an empty recipe needs nothing", [{}, {}], True, hidden=True),
        ],
        hints={
            "2": ("You need to look at every item in the *recipe*, not the "
                  "inventory — the inventory may hold lots of things the recipe "
                  "doesn't care about."),
            "3": ("Loop over the recipe's keys. For each one, find how many you "
                  "have and compare. The tricky part is an item you don't have at "
                  "all: `inventory.get(item, 0)` gives you 0 instead of crashing. "
                  "If any item falls short you can return False immediately."),
            "4": ("The shape is:\n\n"
                  "    for each item and amount in the recipe:\n"
                  "        how_many = inventory.get(item, 0)\n"
                  "        if how_many is less than amount:\n"
                  "            return False\n"
                  "    return True\n\n"
                  "Use `for item, amount in recipe.items():` to get both at once."),
        },
    ),
    # ---------------------------------------------------------------- loops
    ex(
        slug="boss-fight",
        title="How long is this boss fight?",
        theme=TH,
        concept=Concept.LOOPS,
        entrypoint="turns_to_win",
        order=3,
        prompt="""\
The boss has some **hp**. You do some **damage** each turn. But it heals a bit
at the end of every turn it survives.

Write `turns_to_win(hp, damage, heal)` returning how many turns it takes to get
the boss to 0 or below.

Each turn: you hit it, then *if it's still alive* it heals.

If it can never die — you're doing no more damage than it heals — return `-1`
rather than looping forever.

```python
turns_to_win(20, 5, 0)   # -> 4
turns_to_win(20, 5, 5)   # -> -1   it heals back everything
```
""",
        starter='''\
def turns_to_win(hp, damage, heal):
    """Return the number of turns to kill the boss, or -1 if it's impossible."""
    turns = 0
    # Keep hitting until it's dead -- but make sure the loop can end!
    return turns
''',
        tests=[
            t("no healing", [20, 5, 0], 4),
            t("heals a little", [20, 6, 1], 4),
            t("cannot be killed", [20, 5, 5], -1),
            t("heals more than you hit", [20, 3, 9], -1, hidden=True),
            t("one big hit", [10, 10, 3], 1, hidden=True),
        ],
        hints={
            "2": ("Two things to sort out. The loop needs to actually change `hp`, "
                  "and you need to spot the impossible case *before* you start "
                  "looping — otherwise it runs forever."),
            "3": ("The boss can never die if your damage is less than or equal to "
                  "the healing, because it gets back everything you took off. "
                  "Check that first and return -1. Otherwise: loop while hp is "
                  "above 0, subtract damage, count the turn, and only heal if the "
                  "boss is still alive."),
            "4": ("The shape is:\n\n"
                  "    if damage <= heal:\n"
                  "        return -1\n"
                  "    turns = 0\n"
                  "    while hp > 0:\n"
                  "        hp = hp - damage\n"
                  "        turns = turns + 1\n"
                  "        if hp > 0:\n"
                  "            hp = hp + heal\n"
                  "    return turns"),
        },
    ),
    # -------------------------------------------------------------- strings
    ex(
        slug="save-game-names",
        title="Reading the save files",
        theme=TH,
        concept=Concept.STRINGS,
        entrypoint="parse_save",
        order=4,
        prompt="""\
Old games packed everything into the filename. Yours look like this:

```
"lvl12:rogue:840xp"
```

That's **level 12**, a **rogue**, with **840 xp**.

Write `parse_save(name)` that pulls it apart and returns a dictionary:

```python
parse_save("lvl12:rogue:840xp")
# -> {"level": 12, "role": "rogue", "xp": 840}
```

Note `level` and `xp` come back as **numbers**, not text. The `lvl` at the front
and the `xp` at the end are labels, not part of the number.
""",
        starter='''\
def parse_save(name):
    """Turn "lvl12:rogue:840xp" into {"level": 12, "role": "rogue", "xp": 840}."""
    # Split it into three pieces first.
    return {}
''',
        tests=[
            t("a rogue", ["lvl12:rogue:840xp"], {"level": 12, "role": "rogue", "xp": 840}),
            t("a wizard", ["lvl3:wizard:75xp"], {"level": 3, "role": "wizard", "xp": 75}),
            t("level 1, no xp", ["lvl1:knight:0xp"], {"level": 1, "role": "knight", "xp": 0}),
            t("big numbers", ["lvl99:bard:123456xp"],
              {"level": 99, "role": "bard", "xp": 123456}, hidden=True),
        ],
        hints={
            "2": ("Start by splitting on the colons — `name.split(\":\")` gives you "
                  "the three pieces as a list. Then deal with each piece."),
            "3": ("The middle piece is already what you want. The first needs "
                  "`lvl` removed from the front, the last needs `xp` removed from "
                  "the end, and both then need turning into numbers with `int()`. "
                  "`.replace(\"lvl\", \"\")` is one way to strip a label."),
            "4": ("The shape is:\n\n"
                  "    parts = name.split(\":\")\n"
                  "    level = int(parts[0].replace(\"lvl\", \"\"))\n"
                  "    role = parts[1]\n"
                  "    xp = int(parts[2].replace(\"xp\", \"\"))\n"
                  "    return {\"level\": level, \"role\": role, \"xp\": xp}"),
        },
    ),
    # ------------------------------------------------------------ functions
    ex(
        slug="character-sheet",
        title="Building a character",
        theme=TH,
        concept=Concept.FUNCTIONS,
        entrypoint="describe",
        order=5,
        prompt="""\
Three small functions, each doing one job, and one that uses the others. This is
what people mean by *decomposition* — and it's the habit that makes bigger
programs possible.

A character is `{"name": ..., "hp": ..., "level": ...}`.

Write these:

- `power(character)` — level × 10, plus hp
- `is_tough(character)` — True if power is 100 or more
- `describe(character)` — `"Nyx the tough (power 140)"` or `"Nyx (power 40)"`

`describe` must **call the other two**. That's the point of the exercise: don't
recompute the power inside it.
""",
        starter='''\
def power(character):
    """Level x 10, plus hp."""
    return 0


def is_tough(character):
    """True when power is 100 or more."""
    return False


def describe(character):
    """Use power() and is_tough() -- don't recalculate them here."""
    return ""
''',
        tests=[
            t("a tough one", [{"name": "Nyx", "hp": 40, "level": 10}], "Nyx the tough (power 140)"),
            t("not tough", [{"name": "Pip", "hp": 10, "level": 3}], "Pip (power 40)"),
            t("exactly 100 counts as tough",
              [{"name": "Bo", "hp": 0, "level": 10}], "Bo the tough (power 100)", hidden=True),
            t("level zero", [{"name": "Ash", "hp": 5, "level": 0}], "Ash (power 5)", hidden=True),
        ],
        hints={
            "2": ("Fill in `power` first and check it on paper: level 10 with 40 hp "
                  "should give 140. Then `is_tough` should call `power` rather than "
                  "working it out again."),
            "3": ("Each function should do one job and trust the others. "
                  "`is_tough` is just `power(character) >= 100`. `describe` picks "
                  "one of two sentences depending on `is_tough`, and puts the "
                  "number from `power` in the brackets. An f-string is the tidy way "
                  "to build the text: `f\"{name} (power {p})\"`."),
            "4": ("The shape is:\n\n"
                  "    def power(character):\n"
                  "        return character[\"level\"] * 10 + character[\"hp\"]\n\n"
                  "    def is_tough(character):\n"
                  "        return power(character) >= 100\n\n"
                  "    def describe(character):\n"
                  "        p = power(character)\n"
                  "        name = character[\"name\"]\n"
                  "        if is_tough(character):\n"
                  "            return f\"{name} the tough (power {p})\"\n"
                  "        return f\"{name} (power {p})\""),
        },
    ),
    # -------------------------------------------------------------- file io
    ex(
        slug="high-score-table",
        title="The high score table",
        theme=TH,
        concept=Concept.FILE_IO,
        entrypoint="top_scores",
        order=6,
        prompt="""\
The arcade cabinet keeps its scores in a text file, one per line:

```
ZOE,4200
MAX,1180
ABE,9990
```

You get the **whole file as one string**. Write `top_scores(contents, n)` that
returns the top `n` names, highest first.

```python
top_scores("ZOE,4200\\nMAX,1180\\nABE,9990", 2)   # -> ["ABE", "ZOE"]
```

Watch out for a blank line at the end — text files usually have one, and it
isn't a score.
""",
        starter='''\
def top_scores(contents, n):
    """Return the top n names, highest score first."""
    scores = []
    # Split into lines, then pull the name and number out of each.
    return []
''',
        tests=[
            t("three scores, top two", ["ZOE,4200\nMAX,1180\nABE,9990", 2], ["ABE", "ZOE"]),
            t("asking for all of them", ["ZOE,4200\nMAX,1180", 5], ["ZOE", "MAX"]),
            t("a trailing newline is not a score", ["ZOE,4200\nMAX,1180\n", 2], ["ZOE", "MAX"]),
            t("empty file", ["", 3], [], hidden=True),
            t("blank lines in the middle", ["ZOE,10\n\nMAX,20\n", 2], ["MAX", "ZOE"], hidden=True),
        ],
        hints={
            "2": ("Two steps: turn the text into a list of (score, name) pairs, "
                  "then sort. `contents.split(\"\\n\")` gives you the lines — but "
                  "some of them may be empty, and an empty line has no comma to "
                  "split on."),
            "3": ("Skip any line that's blank after `.strip()`. For the rest, split "
                  "on the comma: the first part is the name, the second needs "
                  "`int()`. Collect them as `(score, name)` tuples, sort with "
                  "`reverse=True` so the biggest is first, then take the first `n` "
                  "with a slice and pull out just the names."),
            "4": ("The shape is:\n\n"
                  "    rows = []\n"
                  "    for line in contents.split(\"\\n\"):\n"
                  "        if line.strip() == \"\":\n"
                  "            continue\n"
                  "        name, score = line.split(\",\")\n"
                  "        rows.append((int(score), name))\n"
                  "    rows.sort(reverse=True)\n"
                  "    return [name for score, name in rows[:n]]"),
        },
    ),
]
