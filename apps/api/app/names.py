"""Tidying the name someone gives us.

One rule, applied where a display name is written rather than where it is read,
so the value in the database is the value on the screen and nothing has to
remember to format it.
"""


def normalise_display_name(value: str) -> str:
    """Trim, and capitalise the first letter. Leave the rest completely alone.

    "benji" becomes "Benji", which is the whole point -- a greeting that reads
    "Welcome back, benji" looks like a bug even though the learner typed it.

    Only the first character, and only when it is lowercase. `.title()` and
    `.capitalize()` both look tempting here and both damage real names:

        .capitalize()   "McDonald" -> "Mcdonald",  "JJ" -> "Jj"
        .title()        "de Silva" -> "De Silva",  "O'Neill" -> "O'Neill" (ok)
                        but also  "JJ" -> "Jj"

    People are entitled to the capitalisation they chose past the first letter,
    and a name is not a sentence. Slicing is the only safe operation.
    """
    cleaned = value.strip()
    if not cleaned:
        return cleaned
    return cleaned[0].upper() + cleaned[1:]
