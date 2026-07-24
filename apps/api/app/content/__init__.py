"""The exercise library -- the theme x concept grid, as data.

This is the most important artefact in the project. Everything else is
machinery; these are the exercises that determine whether the central claim can
be tested at all.

Split across modules by world so the content track can be worked on by more than
one person without constant merge conflicts:

    games.py     records with state       quests, inventories, scores
    sports.py    aggregation over groups  leagues, tallies, streaks
    space.py     sequences and order      flight plans, fuel, telemetry
    music.py     pairings and patterns    playlists, overlaps, rhythm
    stories.py   generation and change    word games, generators
    generic.py   the control condition    the study set's twins

Two rules every exercise here obeys. Both are checked by tests.

  1. The world determines the DATA SHAPE and the PROBLEM, never just the names.
     Strip the world and the problem should change. If only the identifiers
     change, the exercise is wrong.

  2. A study-set exercise and its generic twin are identical in everything but
     framing -- same concept, same tests verbatim, same visible/hidden split,
     same hint ladder depth and specificity. Anything else and the study
     measures that difference instead of framing.

FILE HANDLING, and why it looks unusual: exercises tagged FILE_IO take the
file's *contents* as a string rather than opening a path. Pyodide has a virtual
in-memory filesystem and the sandbox container has a real read-only one, so
`open("scores.txt")` would resolve differently in each -- precisely the
run/submit divergence the shared harness exists to prevent. Students still
practise the part that matters (splitting lines, parsing fields, coping with a
trailing newline) and the two environments cannot disagree.
"""

from ..models import Concept, Theme, ThemeVariant
from .games import GAMES
from .generic import GENERIC_TWINS
from .music import MUSIC
from .space import SPACE
from .sports import SPORTS
from .stories import STORIES

__all__ = [
    "ALL_EXERCISES",
    "STUDY_SET_PAIRS",
    "Concept",
    "Theme",
    "ThemeVariant",
]

ALL_EXERCISES = [*GAMES, *SPORTS, *SPACE, *MUSIC, *STORIES, *GENERIC_TWINS]

# The six exercises used in the within-subjects comparison, one per concept so
# that concept is held constant across conditions and cannot confound the
# result. Each has a generic twin in generic.py sharing its pair_id.
STUDY_SET_PAIRS = [
    "expired-quests",       # lists
    "league-table",         # dicts
    "fuel-check",           # loops
    "setlist-printer",      # strings
    "story-generator",      # functions
    "season-file",          # file handling
]
