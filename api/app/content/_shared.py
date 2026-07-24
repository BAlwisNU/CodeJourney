"""Helpers shared by every world module."""

from ..models import Concept, Theme, ThemeVariant

# Default ladder thresholds. Per-exercise overrides go in the exercise itself --
# see services/hints.py for why these are configurable at all.
T = {
    "l2_after_failures": 2,
    "l3_after_failures": 4,
    "l4_after_failures": 6,
    "l2_after_idle_seconds": 300,
}


def ex(
    *,
    slug: str,
    title: str,
    theme: Theme,
    concept: Concept,
    entrypoint: str,
    prompt: str,
    starter: str,
    tests: list,
    hints: dict,
    order: int,
    pair_id: str | None = None,
    variant: ThemeVariant = ThemeVariant.THEMED,
) -> dict:
    """Build an exercise row.

    `pair_id` defaults to the slug, which keeps the UNIQUE(pair_id, variant)
    constraint satisfied for exercises that have no twin. Only study-set
    exercises share a pair_id with a real twin.
    """
    return dict(
        slug=slug,
        title=title,
        theme=theme,
        concept=concept,
        variant=variant,
        pair_id=pair_id or slug,
        entrypoint=entrypoint,
        prompt_md=prompt,
        starter_code=starter,
        tests=tests,
        hints=hints,
        hint_thresholds=T,
        order_index=order,
    )


def t(name: str, args: list, expected, hidden: bool = False) -> dict:
    """One test case.

    Keep at least one visible test per exercise -- hidden tests exist to stop
    hardcoding, not to make feedback unactionable.
    """
    return {"name": name, "args": args, "expected": expected, "hidden": hidden}
