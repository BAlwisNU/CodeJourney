"""The exercise library -- the theme x concept grid, as data.

This is the most important artefact in the project. Everything else is
machinery; these are the exercises that determine whether the central claim can
be tested at all.

Split across modules by world so the content track can be worked on by more than
one person without constant merge conflicts:

    games.py     records with state       quests, inventories, scores   [written]
    sports.py    aggregation over groups  leagues, tallies, streaks     [to do]
    space.py     sequences and order      flight plans, fuel, telemetry [to do]
    music.py     pairings and patterns    playlists, overlaps, rhythm   [to do]
    stories.py   generation and change    word games, generators        [to do]
    generic.py   the control condition    the study set's twins         [to do]

`WORLD_MODULES` lists the exercise lists that currently exist. Add a world's
export here as it lands; `ALL_EXERCISES` picks it up automatically, so seeding a
new world is a one-line change rather than a scavenger hunt.

Two rules every exercise obeys. Both are checked by tests.

  1. The world determines the DATA SHAPE and the PROBLEM, never just the names.
     Strip the world and the problem should change. If only the identifiers
     change, the exercise is wrong.

  2. A study-set exercise and its generic twin are identical in everything but
     framing -- same concept, same tests verbatim, same visible/hidden split,
     same hint ladder depth and specificity.

FILE HANDLING looks unusual: FILE_IO exercises take the file's *contents* as a
string rather than opening a path. Pyodide has a virtual in-memory filesystem
and the sandbox has a real read-only one, so `open("scores.txt")` would resolve
differently in each -- the run/submit divergence the shared harness exists to
prevent. Students still practise splitting lines and parsing fields; the two
environments cannot disagree.
"""

from .games import GAMES
from .lessons import LESSONS

# Every world's exercise list that exists today. Extend as worlds are written.
WORLD_MODULES = [GAMES, LESSONS]

ALL_EXERCISES = [ex for module in WORLD_MODULES for ex in module]

# The six exercises intended for the within-subjects comparison, one per concept
# so that concept is held constant across conditions. Each needs a generic twin
# sharing its pair_id (twins live in generic.py, still to write).
STUDY_SET_SLUGS = [
    "expired-quests",       # lists    (twin: filter-records-generic -- seeded inline for now)
    "league-table",         # dicts
    "fuel-check",           # loops
    "setlist-printer",      # strings
    "story-generator",      # functions
    "season-file",          # file handling
]

__all__ = ["ALL_EXERCISES", "GAMES", "LESSONS", "STUDY_SET_SLUGS", "WORLD_MODULES"]
