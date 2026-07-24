"""Beginner-friendly translations of Python errors.

A deterministic table, not a model. ~25 rules cover the overwhelming majority of
errors novices actually hit, and the table wins on every axis that matters here:
it is instant (no network round trip while a student waits), free, identical
every time, and defensible in a report -- "we built a rule table from the novice
error literature" is a contribution; "we asked a model" is not.

An LLM is the fallback for the long tail, and only that. It is not wired up yet;
`translate()` returns a safe generic message when nothing matches, which is
strictly better than showing a raw traceback.

Three rules for writing a translation:

  1. Say what happened, in words a two-week beginner knows. No jargon that
     itself needs explaining ("iterable", "unhashable", "callable").
  2. Point at the line THEY wrote. The harness already resolves this.
  3. Never give the fix. This is L1 of the ladder -- the hint levels above it do
     the teaching, and a translation that solves the exercise skips the learning.

Every rule is (matcher, template). Matchers are checked in order and the first
hit wins, so put specific patterns above general ones.
"""

import re
from collections.abc import Callable

# --- helpers ---------------------------------------------------------------


def _name_from(message: str) -> str | None:
    match = re.search(r"name '([^']+)' is not defined", message)
    return match.group(1) if match else None


def _attr_from(message: str) -> tuple[str, str] | None:
    match = re.search(r"'([^']+)' object has no attribute '([^']+)'", message)
    return (match.group(1), match.group(2)) if match else None


def _friendly_type(name: str) -> str:
    return {
        "str": "a piece of text",
        "int": "a whole number",
        "float": "a decimal number",
        "list": "a list",
        "dict": "a dictionary",
        "tuple": "a tuple",
        "bool": "True or False",
        "NoneType": "nothing (None)",
        "set": "a set",
        "function": "a function",
    }.get(name, f"a {name}")


# --- the table -------------------------------------------------------------
#
# Each entry: (error type, substring or regex to match in the message, builder).
# `builder` receives the raw message and returns the student-facing sentence.

Rule = tuple[str, str | None, Callable[[str], str]]

RULES: list[Rule] = [
    # --- NameError ---------------------------------------------------------
    (
        "NameError",
        None,
        lambda m: (
            f"You've used the name “{_name_from(m)}”, but Python hasn't seen it "
            "before. Either it's spelled differently from where you created it, "
            "or it hasn't been created yet."
            if _name_from(m)
            else "You've used a name Python hasn't seen before."
        ),
    ),
    # --- SyntaxError family ------------------------------------------------
    (
        "SyntaxError",
        "was never closed",
        lambda m: (
            "You opened a bracket and never closed it. Python read to the end of "
            "the file still waiting for the matching one."
        ),
    ),
    (
        "SyntaxError",
        "invalid syntax",
        lambda m: (
            "Python got to this point and couldn't make sense of it. The usual "
            "causes are a missing colon at the end of an if/for/def line, a "
            "missing bracket, or = where you meant ==."
        ),
    ),
    (
        "SyntaxError",
        "expected ':'",
        lambda m: (
            "Python expected a colon here. Lines that start a block — if, for, "
            "while, def — end with one."
        ),
    ),
    (
        "SyntaxError",
        "cannot assign to",
        lambda m: (
            "This is trying to put a value into something that can't hold one. "
            "Remember = means “put this value in here”, and == means “are these "
            "the same?”."
        ),
    ),
    (
        "SyntaxError",
        None,
        lambda m: (
            "Python couldn't read your code as Python. Something about the shape "
            "of this line is off — a bracket, a quote, or a colon."
        ),
    ),
    (
        "IndentationError",
        "unexpected indent",
        lambda m: (
            "This line is indented further than Python expected. Indentation is "
            "how Python knows what's inside what, so the extra space changes the "
            "meaning."
        ),
    ),
    (
        "IndentationError",
        "expected an indented block",
        lambda m: (
            "Python expected an indented line here. After a line ending in a "
            "colon, the lines belonging to it are indented."
        ),
    ),
    (
        "IndentationError",
        None,
        lambda m: (
            "The indentation here doesn't line up. Python uses indentation to "
            "tell what belongs inside what, so it has to be consistent."
        ),
    ),
    (
        "TabError",
        None,
        lambda m: (
            "This file mixes tabs and spaces for indentation. They look the same "
            "on screen but Python treats them differently — pick one."
        ),
    ),
    # --- TypeError ---------------------------------------------------------
    (
        "TypeError",
        "not supported between instances",
        lambda m: (
            "You're comparing two things that can't be compared — like asking "
            "whether a word is smaller than a number."
        ),
    ),
    (
        "TypeError",
        "can only concatenate str",
        lambda m: (
            "You're adding text to something that isn't text. Python won't guess "
            "what you meant — turn the other value into text first, with str()."
        ),
    ),
    (
        "TypeError",
        "unsupported operand type",
        lambda m: (
            "These two values can't be combined this way — the operation doesn't "
            "make sense for those kinds of value."
        ),
    ),
    (
        "TypeError",
        "object is not subscriptable",
        lambda m: (
            "You're using square brackets on something that doesn't have "
            "positions or keys to look up."
        ),
    ),
    (
        "TypeError",
        "object is not iterable",
        lambda m: (
            "You're trying to loop over something that isn't a collection of "
            "items."
        ),
    ),
    (
        "TypeError",
        "object is not callable",
        lambda m: (
            "You've put brackets after something that isn't a function, so Python "
            "tried to call it and couldn't."
        ),
    ),
    (
        "TypeError",
        "positional argument",
        lambda m: (
            "This function was given the wrong number of values. Check how many "
            "it's defined to take against how many you passed."
        ),
    ),
    (
        "TypeError",
        "'NoneType'",
        lambda m: (
            "Something here is None — nothing at all. That often means a function "
            "you called didn't return anything, usually a missing return."
        ),
    ),
    (
        "TypeError",
        None,
        lambda m: "Something here is the wrong kind of value for what's being done to it.",
    ),
    # --- lookup errors -----------------------------------------------------
    (
        "IndexError",
        None,
        lambda m: (
            "You asked for an item at a position that doesn't exist — the list is "
            "shorter than that. Remember the first item is at 0, so a list of 3 "
            "items has positions 0, 1 and 2."
        ),
    ),
    (
        "KeyError",
        None,
        lambda m: (
            "You looked up a key that isn't in the dictionary. Check the spelling "
            "and the capitalisation — they have to match exactly."
        ),
    ),
    (
        "AttributeError",
        None,
        lambda m: (
            (
                lambda pair: (
                    f"You asked for “.{pair[1]}” on {_friendly_type(pair[0])}, "
                    "which doesn't have that. It's often a typo, or the value "
                    "isn't the kind of thing you were expecting."
                )
                if pair
                else "You asked for something the value doesn't have."
            )(_attr_from(m))
        ),
    ),
    # --- value & maths -----------------------------------------------------
    (
        "ValueError",
        "invalid literal for int",
        lambda m: (
            "You tried to turn text into a whole number, but the text isn't a "
            "number Python can read."
        ),
    ),
    (
        "ValueError",
        "not enough values to unpack",
        lambda m: (
            "You're splitting something into several variables, but there weren't "
            "enough pieces to go around."
        ),
    ),
    (
        "ValueError",
        None,
        lambda m: (
            "The value passed in was the right kind of thing but not an acceptable "
            "one."
        ),
    ),
    (
        "ZeroDivisionError",
        None,
        lambda m: (
            "Something was divided by zero. If you're working out an average, this "
            "usually means the list was empty."
        ),
    ),
    # --- structural --------------------------------------------------------
    (
        "RecursionError",
        None,
        lambda m: (
            "A function kept calling itself and never stopped. A function that "
            "calls itself needs a case where it stops and just returns."
        ),
    ),
    (
        "ImportError",
        None,
        lambda m: "Python couldn't find something you tried to import.",
    ),
    (
        "ModuleNotFoundError",
        None,
        lambda m: (
            "Python couldn't find that module. These exercises only need Python's "
            "built-in tools — nothing needs installing."
        ),
    ),
    (
        "UnboundLocalError",
        None,
        lambda m: (
            "You're using a variable inside a function before giving it a value "
            "there."
        ),
    ),
    (
        "StopIteration",
        None,
        lambda m: "Something ran out of items before it was finished.",
    ),
    # --- ours --------------------------------------------------------------
    (
        "Timeout",
        None,
        lambda m: (
            "Your program was still running after 5 seconds, so it was stopped. "
            "That almost always means a loop whose condition never becomes false."
        ),
    ),
    (
        "MissingFunction",
        None,
        # The harness already writes a clear sentence for this one.
        lambda m: m,
    ),
]


def translate(error: dict | None) -> str | None:
    """Turn a harness error dict into one plain-English sentence.

    Returns None when there's no error. Never returns a traceback, and never
    returns None for an error that exists -- an unrecognised error still gets a
    generic-but-human message, because a beginner facing raw Python output is
    the exact failure this whole project exists to fix.
    """
    if not error:
        return None

    kind = error.get("type", "")
    message = error.get("message", "")

    for rule_type, needle, build in RULES:
        if rule_type != kind:
            continue
        if needle is not None and needle not in message:
            continue
        return build(message)

    # Unknown error. Say something true and useful rather than nothing.
    return (
        f"Your program stopped with a {kind}. That's Python's way of saying it "
        "couldn't finish. The raw message is below if you want to look."
    )


def locate(error: dict | None) -> str | None:
    """The 'where to look' half of L1, kept separate from the 'what happened'.

    Split because the line number comes from the harness and the explanation
    comes from the table -- and because a translation with no line is still
    worth showing.
    """
    if not error:
        return None
    line = error.get("line")
    if line is None:
        return None
    return f"Look at line {line}."
