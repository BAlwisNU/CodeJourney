"""Seed data: one exercise pair, demonstrating what a themed exercise has to be.

Read the two exercises below side by side. They share a `pair_id`, a concept, a
data shape, an argument list, and an expected-value list -- identical tests,
identical difficulty. The ONLY thing that differs is the framing.

That is the discipline this whole project depends on, and it is worth being blunt
about the failure mode it avoids:

    NOT a themed exercise:
        "Write a function that adds two numbers. Call them quest_1 and quest_2."

That is a generic exercise wearing a hat. A marker sees through it instantly and
so does a student. The theme has to determine the *data shape and the problem*,
not the identifiers.

Here, the Games world generates records with state, which is why the natural
question is "which quests have expired?" -- a filter over dated records. The
generic twin asks for a filter over dated records too, because it must, or the
comparison measures difficulty instead of framing. See
docs/theme-concept-grid.md for the full 5x6 grid this pair is the first cell of.
"""



from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import hash_password
from .db import SessionLocal, engine
from .content.games import GAMES as GAMES_LIBRARY
from .content.lessons import LESSONS as LESSON_LIBRARY
from .models import (
    Base,
    Concept,
    Exercise,
    Lesson,
    ParsonsProblem,
    QuizQuestion,
    Role,
    Theme,
    ThemeVariant,
    User,
)

# Shared by both sides of the pair. Same inputs, same expected outputs, so any
# measured difference between the two is attributable to framing and nothing else.
_TESTS = [
    {
        "name": "one expired, one still live",
        "args": [
            [
                {"name": "Slay the dragon", "due_day": 10, "done": False},
                {"name": "Find the lost sword", "due_day": 30, "done": False},
            ],
            15,
        ],
        "expected": ["Slay the dragon"],
        "hidden": False,
    },
    {
        "name": "completed quests never expire",
        "args": [
            [
                {"name": "Slay the dragon", "due_day": 10, "done": True},
                {"name": "Rescue the baker", "due_day": 5, "done": False},
            ],
            15,
        ],
        "expected": ["Rescue the baker"],
        "hidden": False,
    },
    {
        "name": "nothing expired yet",
        "args": [
            [{"name": "Slay the dragon", "due_day": 10, "done": False}],
            5,
        ],
        "expected": [],
        "hidden": False,
    },
    {
        "name": "expiring today has not expired yet",
        "args": [
            [{"name": "Slay the dragon", "due_day": 10, "done": False}],
            10,
        ],
        "expected": [],
        # Hidden because it's the boundary case students hardcode around.
        # Every other test here is visible -- hidden tests exist to stop
        # gaming, not to make feedback unactionable.
        "hidden": True,
    },
    {
        "name": "an empty quest log",
        "args": [[], 20],
        "expected": [],
        "hidden": True,
    },
]

_THRESHOLDS = {
    "l2_after_failures": 2,
    "l3_after_failures": 4,
    "l4_after_failures": 6,
    "l2_after_idle_seconds": 300,
}

PAIR_ID = "00000000-0000-0000-0000-0000000000a1"

# Defined as plain dicts, not Exercise instances. A module-level ORM object binds
# to the first Session that touches it and is detached forever after, which makes
# seed() single-use -- fine in production, broken in tests, and a landmine either
# way. seed() constructs fresh instances from these on every call.
THEMED = dict(
    slug="expired-quests",
    title="The quest log",
    theme=Theme.GAMES,
    concept=Concept.LISTS,
    variant=ThemeVariant.THEMED,
    pair_id=PAIR_ID,
    entrypoint="expired_quests",
    prompt_md="""\
Every RPG has a quest log, and every quest log has that one job you meant to do
forty hours ago. You're building the bit that finds them.

Each quest is a **name**, the **day it expires**, and whether you've **done** it:

```python
{"name": "Slay the dragon", "due_day": 10, "done": False}
```

`today` is just a number — day 15, say.

Write `expired_quests(quests, today)`. It returns a **list of the names** of the
quests you never finished and whose day has already gone, in the order they
appear in the log.

A quest expiring *today* hasn't expired yet. You've still got today.

```python
quests = [
    {"name": "Slay the dragon",     "due_day": 10, "done": False},
    {"name": "Find the lost sword", "due_day": 30, "done": False},
]
expired_quests(quests, 15)   # -> ["Slay the dragon"]
```
""",
    starter_code='''\
def expired_quests(quests, today):
    """Return the names of quests that aren't done and are past their day."""
    expired = []
    # Go through each quest and decide whether it belongs in the list.
    return expired
''',
    tests=_TESTS,
    hints={
        # L2 -- location. Points at where, not what.
        "2": (
            "Look at the loop. For each quest you need to check *two* things "
            "before adding it: has the day gone, and is it still not done? "
            "Right now `expired` is being returned exactly as it started."
        ),
        # L3 -- conceptual. Names the idea, doesn't write it.
        "3": (
            "Filtering a list means: start with an empty list, look at every "
            "item, and append only the ones that pass your test. Your test here "
            "is a quest whose `due_day` is *before* today AND whose `done` is "
            "False. Remember you want the quest's name in the result, not the "
            "whole quest."
        ),
        # L4 -- structure. Pseudocode skeleton. Still not the answer.
        "4": (
            "The shape is:\n\n"
            "    make an empty list\n"
            "    for each quest in quests:\n"
            "        if the quest's due_day is less than today:\n"
            "            if the quest is not done:\n"
            "                add the quest's name to your list\n"
            "    return the list\n\n"
            "You get at a quest's name with quest['name']."
        ),
    },
    hint_thresholds=_THRESHOLDS,
    order_index=1,
)

GENERIC = dict(
    slug="filter-records-generic",
    title="Filter a list of records",
    theme=Theme.GENERIC,
    concept=Concept.LISTS,
    variant=ThemeVariant.GENERIC,
    pair_id=PAIR_ID,
    entrypoint="filter_records",
    # Same problem, same data shape, same tests. Stripped of any world at all.
    # This is the control condition: if the study finds a difference, this is
    # what it is a difference *from*.
    prompt_md="""\
You are given a list of records. Each record is a dictionary with a **name**, a
**due_day**, and a **done** flag:

```python
{"name": "Item A", "due_day": 10, "done": False}
```

You are also given an integer `threshold`.

Write `filter_records(records, threshold)` that returns a **list of the names**
of the records where `done` is `False` and `due_day` is less than `threshold`,
in the order they appear.

```python
records = [
    {"name": "Item A", "due_day": 10, "done": False},
    {"name": "Item B", "due_day": 30, "done": False},
]
filter_records(records, 15)   # -> ["Item A"]
```
""",
    starter_code='''\
def filter_records(records, threshold):
    """Return the names of records that are not done and below the threshold."""
    result = []
    # Go through each record and decide whether it belongs in the list.
    return result
''',
    tests=_TESTS,
    hints={
        # Deliberately parallel to the themed hints in length, specificity and
        # ladder depth. If the control's hints were worse, the study would be
        # measuring hint quality, not framing.
        "2": (
            "Look at the loop. For each record you need to check *two* things "
            "before adding it: is `due_day` below the threshold, and is `done` "
            "still False? Right now `result` is being returned exactly as it "
            "started."
        ),
        "3": (
            "Filtering a list means: start with an empty list, look at every "
            "item, and append only the ones that pass your test. Your test here "
            "is a record whose `due_day` is less than `threshold` AND whose "
            "`done` is False. Remember you want the record's name in the "
            "result, not the whole record."
        ),
        "4": (
            "The shape is:\n\n"
            "    make an empty list\n"
            "    for each record in records:\n"
            "        if the record's due_day is less than threshold:\n"
            "            if the record is not done:\n"
            "                add the record's name to your list\n"
            "    return the list\n\n"
            "You get at a record's name with record['name']."
        ),
    },
    hint_thresholds=_THRESHOLDS,
    order_index=2,
)


# ---------------------------------------------------------------------------
# The Plan stage: one lesson + quiz + Parsons warm-up for Lists.
#
# Keyed to the CONCEPT, not the exercise, so the themed exercise and its generic
# twin share identical teaching. If the themed side had a better lesson, the
# study would be measuring teaching quality rather than framing.
# ---------------------------------------------------------------------------

LESSON = dict(
    slug="lists-filtering",
    title="Picking things out of a list",
    concept=Concept.LISTS,
    order_index=1,
    body_md="""\
## Picking things out of a list

A **list** holds several things in order. Each thing has a position, and the
first position is `0` — not 1. That trips everyone up at first.

```python
quests = ["Slay the dragon", "Find the sword", "Rescue the baker"]
quests[0]        # "Slay the dragon"
len(quests)      # 3
```

### Looking at each thing in turn

A `for` loop hands you the items one at a time:

```python
for quest in quests:
    print(quest)
```

### Keeping only some of them

This pattern comes up constantly, and it's worth learning as a shape:

1. Make an empty list to collect into.
2. Loop over everything.
3. `if` the item passes your test, `append` it.
4. Return the collected list.

```python
short_ones = []
for quest in quests:
    if len(quest) < 10:
        short_ones.append(quest)
return short_ones
```

That's called **filtering**, and once you can see it you'll see it everywhere.

### Lists of dictionaries

Often each item is a **dictionary** — a thing with named parts:

```python
goal = {"name": "Slay the dragon", "due_day": 10, "done": False}
goal["name"]      # "Run 5k"
goal["done"]      # False
```

So filtering a list of these means looking *inside* each one:

```python
if quest["done"]:
    ...
```

### One thing to watch

`<` and `<=` are not the same. If a quest expires on day 10 and today is day
10, is it gone? Deciding exactly where your boundary sits is most of the work in
problems like this — and it's where most bugs live.
""",
)

QUIZ = [
    dict(
        prompt="What does `quests[0]` give you?",
        options=[
            "The first item",
            "The second item",
            "The whole list",
            "An error — lists start at 1",
        ],
        correct_index=0,
        explanation=(
            "Positions start at 0, so `quests[0]` is the first item. A list of 3 "
            "things has positions 0, 1 and 2 — which is why `goals[3]` would be "
            "an error."
        ),
        order_index=1,
    ),
    dict(
        prompt="You want to keep only some items from a list. What do you do first?",
        options=[
            "Make an empty list to collect into",
            "Delete the items you don't want",
            "Sort the list",
            "Count how many there are",
        ],
        correct_index=0,
        explanation=(
            "Start with an empty list, then append the ones that pass your test. "
            "Removing items from a list while you're looping over it causes "
            "strange bugs, so collecting into a new list is the safer habit."
        ),
        order_index=2,
    ),
    dict(
        prompt='Given `quest = {"name": "Slay the dragon", "done": False}`, how do you get "Slay the dragon"?',
        options=['quest["name"]', "quest.name", "quest[0]", 'quest("name")'],
        correct_index=0,
        explanation=(
            "Dictionaries are looked up by key in square brackets: "
            '`quest["name"]`. The quotes matter — without them Python thinks '
            "`name` is a variable."
        ),
        order_index=3,
    ),
    dict(
        prompt="Something is due on day 10 and today is day 10. Using `due_day < today`, is it overdue?",
        options=[
            "No — 10 is not less than 10",
            "Yes — it's due now",
            "Yes — < includes equal",
            "It depends on the list",
        ],
        correct_index=0,
        explanation=(
            "`10 < 10` is False, so it isn't counted as overdue. This is exactly "
            "the boundary decision the exercise turns on: `<` means strictly "
            "before, `<=` would include today."
        ),
        order_index=4,
    ),
]

PARSONS_LINES = [
    "def expired_quests(quests, today):",
    "    expired = []",
    "    for quest in quests:",
    "        if quest[\"due_day\"] < today and not quest[\"done\"]:",
    "            expired.append(quest[\"name\"])",
    "    return expired",
]

PARSONS_DISTRACTORS = [
    # Plausible, and each one is a real novice mistake rather than nonsense:
    # returning inside the loop, and the <= boundary slip.
    "    return expired[0]",
    "        if quest[\"due_day\"] <= today:",
]


def seed(db: Session) -> None:
    if db.scalar(select(User).where(User.email == "student@example.com")) is None:
        db.add(
            User(
                email="student@example.com",
                password_hash=hash_password("password123"),
                display_name="Test Student",
                role=Role.STUDENT,
                counterbalance_group="A",
            )
        )
        db.add(
            User(
                email="instructor@example.com",
                password_hash=hash_password("password123"),
                display_name="Test Instructor",
                role=Role.INSTRUCTOR,
            )
        )

    for spec in (THEMED, GENERIC):
        if db.scalar(select(Exercise).where(Exercise.slug == spec["slug"])) is None:
            db.add(Exercise(**spec))

    # The rest of the Games world -- 5 more lessons across the other concepts.
    # Skip the quest log: the inline pair above already seeds it as the study
    # exercise, and re-adding it would collide on its unique slug.
    for spec in GAMES_LIBRARY:
        if spec["slug"] == "expired-quests":
            continue
        if db.scalar(select(Exercise).where(Exercise.slug == spec["slug"])) is None:
            db.add(Exercise(**spec))

    # The rest of the curriculum -- one focused lesson per remaining module.
    # Strip underscore keys (e.g. _solution) that aren't columns on Exercise.
    for spec in LESSON_LIBRARY:
        if db.scalar(select(Exercise).where(Exercise.slug == spec["slug"])) is None:
            row = {k: v for k, v in spec.items() if not k.startswith("_")}
            db.add(Exercise(**row))

    db.commit()

    # --- the Plan stage ---------------------------------------------------
    lesson = db.scalar(select(Lesson).where(Lesson.slug == LESSON["slug"]))
    if lesson is None:
        lesson = Lesson(**LESSON)
        db.add(lesson)
        db.flush()  # need the id for the questions
        for question in QUIZ:
            db.add(QuizQuestion(lesson_id=lesson.id, **question))

    # Parsons warm-up, attached to the themed exercise. The generic twin gets
    # the same lines with its own names -- both sides of a pair must get the
    # same scaffolding or the comparison measures support, not framing.
    for slug, entry in (
        ("expired-quests", "expired_quests"),
        ("filter-records-generic", "filter_records"),
    ):
        exercise = db.scalar(select(Exercise).where(Exercise.slug == slug))
        if exercise is None:
            continue
        if db.scalar(
            select(ParsonsProblem).where(ParsonsProblem.exercise_id == exercise.id)
        ):
            continue

        if entry == "filter_records":
            lines = [
                line.replace("expired_quests", "filter_records")
                .replace("quests", "records")
                .replace("quest", "record")
                .replace("today", "threshold")
                .replace("expired", "result")
                for line in PARSONS_LINES
            ]
            distractors = [
                line.replace("quest", "record")
                .replace("today", "threshold")
                .replace("expired", "result")
                for line in PARSONS_DISTRACTORS
            ]
        else:
            lines, distractors = PARSONS_LINES, PARSONS_DISTRACTORS

        db.add(
            ParsonsProblem(
                exercise_id=exercise.id,
                prompt=(
                    "Drag these into the right order to build the function. "
                    "Two of the lines don't belong — leave them out."
                ),
                lines=lines,
                distractors=distractors,
            )
        )

    db.commit()


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    from .content import ALL_EXERCISES
    print(f"seeded: 2 users, {len(ALL_EXERCISES) + 1} exercises, 1 lesson + quiz, 2 Parsons")


if __name__ == "__main__":
    main()
