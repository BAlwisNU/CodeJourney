"""The tutor -- the one MODULE an LLM is allowed into the platform.

It used to be one conversation; it is now three jobs. The claim that matters is
unchanged: every call to a model in this codebase is made from this file, so
there is exactly one place to audit what a model is ever told.

  chat()             a friendly-teacher conversation at the Reflect stage. It
                     talks about the lesson and the student's code, gauges how
                     secure they feel, and may OFFER to build more practice.
  welcome_chat()     step three of signing up: a relaxed conversation about what
                     someone is interested in and what they might build, which
                     ends in a plan of topics and project ideas. Sees the signup
                     answers and nothing else -- no code, no submissions.
  generate_exercise() when the student accepts an offer, it builds a brand-new
                     practice exercise and proves it solvable through the real
                     harness before it is ever shown.

The hard boundary this module respects, and the reason it can exist at all:

    It never sees the private journal.

The tried/stuck/fixed journal (routers/reflections.py) is structurally kept away
from every LLM, because a student may disclose real distress there and the
platform promises no psychological judgement. This tutor is a DIFFERENT thing --
an opt-in conversation the student starts, scoped to the code and the concept.
The only student-authored text it sees is the code they wrote and chose to run.
Everything the model is told is assembled here, from the exercise and the
student's own submissions; the browser cannot inject instructions.

No API key => `enabled()` is False and the callers degrade to a friendly note.
The key comes from the environment (ANTHROPIC_API_KEY); it is never committed.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass
from functools import lru_cache

from ..config import get_settings
from ..models import Concept, Theme, ThemeVariant
from .grading import get_runner

logger = logging.getLogger(__name__)
settings = get_settings()

# Kept low: a chat turn doesn't need deep reasoning, and a tutor that takes ten
# seconds to reply stops feeling like a conversation. Thinking is left ON (the
# Opus-5 default) rather than disabled, because disabling it makes the model
# occasionally emit a tool call as plain prose -- which here would silently drop
# the "offer a lesson" action. Low effort keeps it snappy without that risk.
_CHAT_MAX_TOKENS = 1024
_GEN_MAX_TOKENS = 4000
_MAX_GEN_ATTEMPTS = 3


def enabled() -> bool:
    return settings.tutor_enabled


@lru_cache
def _client():
    # Imported lazily so the whole app doesn't hard-depend on the SDK being
    # installed when the tutor is switched off.
    import anthropic

    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LearnerBrief:
    """The teachable parts of what someone told us when they signed up."""

    goals: str = ""
    #: The human-readable label, not the stored key -- the model should be told
    #: "Comfortable in another language, new to Python", not "other_language".
    experience: str = ""
    experience_note: str = ""
    project_ideas: str = ""
    #: From the welcome conversation, not the form: what a model made of talking
    #: to them, and the projects it suggested. Carried here so a lesson months
    #: later still knows what they came for.
    interests: str = ""
    suggested_projects: tuple[str, ...] = ()
    #: What they said they were worried about, as labels. The most actionable
    #: thing on the form: someone who believes they are "not a maths person"
    #: needs that belief addressed, not taught over.
    worries: tuple[str, ...] = ()
    #: Roughly how much time they have, and how they take in something new.
    time_available: str = ""
    learn_style: str = ""

    def is_empty(self) -> bool:
        return not any(
            (
                self.goals,
                self.experience,
                self.experience_note,
                self.project_ideas,
                self.interests,
                self.suggested_projects,
                self.worries,
                self.time_available,
                self.learn_style,
            )
        )


@dataclass
class TutorContext:
    """Everything the tutor is allowed to know. Assembled in the router from the
    exercise and the student's own submissions -- never from the journal."""

    title: str
    concept: str
    prompt_md: str
    entrypoint: str
    latest_code: str | None
    solved: bool
    attempts: int
    last_summary: str | None  # e.g. "2 of 5 checks passing" on the last submit

    #: What the learner said about themselves when they signed up -- their goals,
    #: how much programming they had done, what they want to build. Optional; it
    #: is a skippable step and most of it may be empty.
    #:
    #: This is the second kind of student-authored text the tutor may see, and it
    #: is worth being precise about why it does not breach the rule at the top of
    #: this file. The journal is barred because it is written *for the student* --
    #: a place to say "I felt stupid" -- and a model reading it would break the
    #: promise that nothing there is judged. This is the opposite: written *for
    #: the teacher*, in answer to "what do you want to be able to do?", on a form
    #: that says it is used to tailor lessons. Withholding it would waste the
    #: only thing they were asked to tell us.
    #:
    #: It stays out of generate_exercise() prompts unless deliberately added --
    #: see _LEARNER_GUIDANCE below for what the model is told to do with it.
    learner: "LearnerBrief | None" = None


_SYSTEM = """\
You are a warm, encouraging programming teacher talking with a beginner who has \
just worked through a Python exercise. Your job in this conversation is to help \
them reflect: talk with them about the lesson and where they found it hard, and \
get a genuine read on how confident and secure they feel with the underlying \
idea -- not whether the tests passed, but whether they could do it again on their \
own.

How to talk:
- Sound like a kind human tutor, not a chatbot. Short, friendly turns. One \
question at a time. Never lecture.
- Start by asking how the exercise felt, or reacting to what they say. Draw them \
out. "What part made you stop and think?" beats "Do you understand loops?".
- Praise specifically and honestly. If their code shows they got something, name \
it. Don't flatter.
- If they're stuck on a concept, explain it simply and check it landed -- don't \
just assert it.
- Gauge confidence gently over the conversation. A quiet "shaky, honestly" is a \
signal to slow down and offer more practice.

Offering more practice (important):
- When you notice they'd benefit from more work -- either the whole topic feels \
shaky, or you spot one specific idea they keep missing -- OFFER to build them a \
new practice exercise using the propose_lesson tool.
- Use scope "topic" for general reinforcement of the whole concept, and "concept" \
for a targeted drill on the specific thing you noticed (say what it is in `focus`).
- Only offer when it would genuinely help, and never more than one open offer at \
a time. Always ALSO write a short spoken message when you offer -- tell them what \
you'd build and why, and let them decide. Don't build anything yourself; the \
tool call is only an offer they choose to accept.

You are NOT a grader and you are NOT the exercise's hint system. You never see \
their private journal. Keep every reply focused on the lesson, their code, and \
how they're feeling about the material.\
"""

_PROPOSE_LESSON_TOOL = {
    "name": "propose_lesson",
    "description": (
        "Offer to build the student a new practice exercise. Call this only when "
        "more practice would genuinely help. It is an OFFER -- the student accepts "
        "it with a click; nothing is built from this call alone. Always also write "
        "a short spoken message alongside the call."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["topic", "concept"],
                "description": (
                    "'topic' = general reinforcement of the whole concept; "
                    "'concept' = a targeted drill on one specific thing you noticed."
                ),
            },
            "concept": {
                "type": "string",
                "enum": [c.value for c in Concept],
                "description": "Which concept the practice should be about.",
            },
            "focus": {
                "type": "string",
                "description": (
                    "One or two sentences on exactly what the new exercise should "
                    "drill -- the specific skill or misconception to target."
                ),
            },
            "title": {
                "type": "string",
                "description": "A short, friendly title for the practice exercise.",
            },
            "rationale": {
                "type": "string",
                "description": "A sentence on why this would help this student now.",
            },
        },
        "required": ["scope", "concept", "focus", "title", "rationale"],
    },
}


def _context_block(ctx: TutorContext) -> str:
    lines = [
        "Here is what you know about this student's sitting. Use it, but talk "
        "about the ideas -- don't read this back to them.",
        "",
        f"Exercise: {ctx.title}",
        f"Concept: {ctx.concept}",
        f"Outcome so far: {'solved it' if ctx.solved else 'not solved yet'}"
        f" after {ctx.attempts} graded attempt(s).",
    ]
    if ctx.last_summary:
        lines.append(f"Most recent check result: {ctx.last_summary}.")
    lines += ["", "The lesson they were given:", ctx.prompt_md.strip()]
    if ctx.latest_code:
        code = ctx.latest_code.strip()[:4000]
        lines += [
            "",
            "The code they last wrote:",
            "```python",
            code,
            "```",
        ]
    lines += _learner_lines(ctx.learner)
    return "\n".join(lines)


_LEARNER_GUIDANCE = (
    "This is what they told us about themselves when they signed up. Use it to "
    "pitch your explanations and to pick examples they'd care about. Do not "
    "recite it back at them, do not congratulate them on their goals, and do "
    "not treat it as a promise -- someone who said they want to build a game "
    "still needs today's concept taught properly.\n"
    "If they named something that worries them, do not raise it unprompted and "
    "do not reassure them about it in the abstract. Let it shape what you do: "
    "someone who fears getting stuck needs to be told specifically what they "
    "just got right; someone who thinks they are not a maths person needs to "
    "see that this did not require maths. Someone with a few minutes a week "
    "should not be offered a project that needs an afternoon."
)


def _learner_facts(learner: "LearnerBrief | None") -> list[str]:
    """Just the answers, one per line, skipping any they didn't give.

    Empty answers are omitted rather than sent as "Goals: (none given)". A model
    told a field is blank tends to comment on the blankness, and the step is
    skippable precisely so that skipping costs nothing.
    """
    if learner is None or learner.is_empty():
        return []

    lines = []
    if learner.experience:
        lines.append(f"Experience when they started: {learner.experience}")
    if learner.experience_note:
        lines.append(f"In their words: {learner.experience_note.strip()[:600]}")
    if learner.goals:
        lines.append(f"What they want to be able to do: {learner.goals.strip()[:800]}")
    if learner.project_ideas:
        lines.append(f"What they'd like to build: {learner.project_ideas.strip()[:800]}")
    if learner.interests:
        lines.append(f"From their welcome chat: {learner.interests.strip()[:600]}")
    if learner.suggested_projects:
        lines.append(
            "Projects they were interested in building: "
            + ", ".join(learner.suggested_projects[:4])
        )
    if learner.worries:
        lines.append(
            "What they said worries them about learning to code: "
            + "; ".join(learner.worries[:6])
        )
    if learner.time_available:
        lines.append(f"Time they have for this: {learner.time_available}")
    if learner.learn_style:
        lines.append(f"How they said they take in something new: {learner.learn_style}")
    return lines


def _learner_lines(learner: "LearnerBrief | None") -> list[str]:
    """The same answers, wrapped in instructions, for the reflect-stage tutor."""
    facts = _learner_facts(learner)
    if not facts:
        return []
    return ["", _LEARNER_GUIDANCE, "", *facts]


def _pump(stream):
    """Raw stream events, reduced to the two the interface cares about.

    Yields ``("thinking", None)`` once, the first time a thinking block starts,
    then ``("text", chunk)`` for each text delta.

    Not `stream.text_stream`, which hides the thinking phase entirely. Measured
    on a real turn: the model thinks for about a second and a half before it
    says anything, and that pause is most of the wait. Reporting it lets the
    interface say "thinking" and mean it, instead of showing three dots that
    animate identically whether the model is reasoning or the network died.
    """
    thinking_announced = False
    for event in stream:
        if event.type != "content_block_delta":
            continue
        delta = event.delta
        kind = getattr(delta, "type", "")
        if kind == "thinking_delta" and not thinking_announced:
            thinking_announced = True
            yield ("thinking", None)
        elif kind == "text_delta" and delta.text:
            yield ("text", delta.text)


def chat_stream(ctx: TutorContext, history: list[dict]):
    """The same conversation as `chat`, yielded as it is written.

    Measured, the blocking call takes four to six seconds. That is a long time
    to watch three dots, and it is the single thing that made this feel like a
    form submission rather than someone talking back. Streaming puts the first
    words on screen in well under a second, which is most of the difference
    between the two.

    Yields ``("text", chunk)`` many times, then exactly one terminal event:

        ("done", {"reply": str, "proposal": dict | None})
        ("error", message)

    The proposal can only arrive at the end, and that is a property of the API
    rather than a shortcut: a tool call is assembled from deltas and is not a
    decision until the message completes. The caller persists on `done`.

    Failure degrades exactly as `chat` does -- a friendly line, never a 500.
    The lesson page must not go down because the tutor is having a moment.
    """
    system = _SYSTEM + "\n\n" + _context_block(ctx)
    try:
        with _client().messages.stream(
            model=settings.anthropic_model,
            max_tokens=_CHAT_MAX_TOKENS,
            system=system,
            tools=[_PROPOSE_LESSON_TOOL],
            messages=history,
            output_config={"effort": "low"},
        ) as stream:
            yield from _pump(stream)
            final = stream.get_final_message()
    except Exception:  # noqa: BLE001 -- external dependency; never crash the page
        logger.exception("tutor chat stream failed")
        yield (
            "error",
            "I'm having trouble reaching my brain just now — give it a moment "
            "and try again. Meanwhile, how did that exercise feel to you?",
        )
        return

    reply, proposal = _read_reply(final)
    yield ("done", {"reply": reply, "proposal": proposal})


def _read_reply(response) -> tuple[str, dict | None]:
    """Pull the spoken text and any offer out of a finished message.

    Shared by the streaming and blocking paths so the two cannot disagree about
    what the model said -- including the recovery below, which matters more than
    it looks: a tool call with no text is an offer that arrives mute, and the
    student sees a card appear with nobody having spoken.
    """
    parts: list[str] = []
    proposal: dict | None = None
    for block in response.content:
        if block.type == "text":
            parts.append(block.text)
        elif block.type == "tool_use" and block.name == "propose_lesson":
            proposal = dict(block.input)

    reply = "\n\n".join(p.strip() for p in parts if p.strip()).strip()
    if not reply and proposal:
        reply = (
            f"{proposal.get('rationale', '').strip()} "
            "Want me to put together a bit of practice on that?"
        ).strip()
    if not reply:
        reply = "Tell me a little about how that one went for you."
    return reply, proposal


def chat(ctx: TutorContext, history: list[dict]) -> tuple[str, dict | None]:
    """Return (reply_text, proposal | None).

    `history` is [{role, content}] with roles user/assistant only. Any failure
    talking to the model degrades to a friendly, non-fatal message rather than a
    500 -- a flaky tutor must never take the exercise page down with it.
    """
    system = _SYSTEM + "\n\n" + _context_block(ctx)
    try:
        response = _client().messages.create(
            model=settings.anthropic_model,
            max_tokens=_CHAT_MAX_TOKENS,
            system=system,
            tools=[_PROPOSE_LESSON_TOOL],
            messages=history,
            output_config={"effort": "low"},
        )
    except Exception:  # noqa: BLE001 -- external dependency; never crash the page
        logger.exception("tutor chat call failed")
        return (
            "I'm having trouble reaching my brain just now — give it a moment and "
            "try again. Meanwhile, how did that exercise feel to you?",
            None,
        )

    return _read_reply(response)


# ---------------------------------------------------------------------------
# Generating a verified practice exercise
# ---------------------------------------------------------------------------

_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")

_GEN_SYSTEM = """\
You design a single self-contained Python practice exercise for a beginner, in \
the exact format the CodeJourney harness runs. Output ONLY the JSON object the \
schema asks for -- no commentary.

Hard rules, all enforced by an automated check that will reject your work:
- The exercise is a SINGLE pure function. No input(), no printing for output, no \
file access, no imports beyond the standard library, no randomness.
- `entrypoint` is the function name (a valid Python identifier).
- `reference_solution` defines that function and MUST pass every test.
- `tests_json` is a JSON array of 4 to 6 test cases. Each is \
{"name": str, "args": [ ... ], "expected": ..., "hidden": bool}. `args` is the \
argument list passed to the function; `expected` is the exact return value.
- Every `args` value and every `expected` value must be plain JSON: numbers, \
strings, booleans, null, lists, and objects with STRING keys only. Never use a \
dict with non-string keys and never rely on tuples -- they do not survive JSON \
and the check will reject them.
- At least two tests must be visible (hidden=false). Include at least one tricky \
boundary case, and it's fine to hide that one.
- `starter_code` defines the function with a docstring and a gentle comment, but \
leaves the body for the student -- it must NOT solve the exercise.
- `prompt_md` is short, warm Markdown explaining the task with one worked example.
- `hint_l2`, `hint_l3`, `hint_l4` are a hint ladder that gets more specific but \
NEVER writes the final answer: L2 points at where to look, L3 names the idea, L4 \
gives a pseudocode skeleton.
The exercise must be plainly framed (a "generic" exercise), not wrapped in a \
game or story world.\
"""

_EXERCISE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "entrypoint": {"type": "string"},
        "prompt_md": {"type": "string"},
        "starter_code": {"type": "string"},
        "reference_solution": {"type": "string"},
        "hint_l2": {"type": "string"},
        "hint_l3": {"type": "string"},
        "hint_l4": {"type": "string"},
        "tests_json": {
            "type": "string",
            "description": "A JSON array of 4-6 test-case objects.",
        },
    },
    "required": [
        "title",
        "entrypoint",
        "prompt_md",
        "starter_code",
        "reference_solution",
        "hint_l2",
        "hint_l3",
        "hint_l4",
        "tests_json",
    ],
    "additionalProperties": False,
}


class GenerationError(Exception):
    """The tutor could not build a sound exercise. The caller turns this into a
    gentle apology, never a stack trace in the student's face."""


def _round_trips(value) -> bool:
    """A value means the same after a JSON store/load -- the int-keyed-dict trap
    that once let a whole exercise fail for every student. See test_content.py."""
    try:
        return json.loads(json.dumps(value)) == value
    except (TypeError, ValueError):
        return False


def _validate_tests(raw: str) -> list[dict]:
    tests = json.loads(raw)
    if not isinstance(tests, list) or not (3 <= len(tests) <= 8):
        raise GenerationError("tests must be a list of 3-8 cases")
    cleaned: list[dict] = []
    visible = 0
    for case in tests:
        if not isinstance(case, dict) or "name" not in case or "args" not in case:
            raise GenerationError("a test case is malformed")
        if not isinstance(case["args"], list):
            raise GenerationError("test args must be a list")
        hidden = bool(case.get("hidden", False))
        if not hidden:
            visible += 1
        for field in ("args", "expected"):
            if not _round_trips(case.get(field)):
                raise GenerationError(f"test {field} does not survive JSON")
        cleaned.append(
            {
                "name": str(case["name"])[:120],
                "args": case["args"],
                "expected": case.get("expected"),
                "hidden": hidden,
            }
        )
    if visible == 0:
        raise GenerationError("at least one test must be visible")
    return cleaned


# ---------------------------------------------------------------------------
# The welcome conversation -- step three of signing up
# ---------------------------------------------------------------------------

_WELCOME_SYSTEM = """\
You are a friendly programming mentor having a first, relaxed conversation with \
someone who has just signed up to learn Python. This is not a lesson and not an \
interview. It is the chat you'd have over coffee with someone who has just told \
you they want to learn to code.

What you are here to do:

  * Find out what they're actually into -- their hobbies, their work, what they \
find themselves curious about. Ask about the person, not just the programming.
  * Talk about things they could BUILD that fit those interests. Be concrete and \
specific: "a script that renames all your photos by the date they were taken" \
beats "a file management tool".
  * If they already have an idea, take it seriously. Talk about what it would \
actually involve, and which Python topics it would teach them along the way.
  * Suggest one or two things they might not have thought of, to widen what they \
imagine is possible. Curiosity is the thing you are trying to grow.

How to talk:

  * Warm, plain, and brief. Two or three short paragraphs at most, usually less.
  * ONE question at a time. A list of questions is an interrogation.
  * Never condescend, and never assume they know a term. If you use one, gloss it \
in half a sentence.
  * Do not promise features. You cannot build their app for them; you are \
helping them see a path to building it themselves.
  * If they say they don't know what they're interested in, that is completely \
normal -- help them find it by asking about their day, not by listing options.

When you have enough to be useful -- usually after three or four exchanges, not \
on the first message -- call record_plan to write down what you have understood. \
You can call it again later if the conversation moves on; the newest call wins. \
Always keep talking alongside the call: the plan is a side effect of the \
conversation, never a replacement for it.

Only ever suggest topics from the list the tool gives you. Those are the topics \
this platform actually teaches, and suggesting anything else would be promising \
something that does not exist.\
"""

_RECORD_PLAN_TOOL = {
    "name": "record_plan",
    "description": (
        "Write down what you have understood about this person: what they are "
        "interested in, which topics would serve them, and concrete projects "
        "they could build. Call it once you have something genuinely useful, "
        "and again if the conversation changes it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "interests": {
                "type": "string",
                "description": (
                    "A sentence or two on what this person is into and what "
                    "they want from learning to code. Written about them, for "
                    "them to read."
                ),
            },
            "topics": {
                "type": "array",
                "items": {"type": "string", "enum": [c.value for c in Concept]},
                "description": (
                    "The topics that best serve what they want to build, most "
                    "useful first. Between one and four."
                ),
            },
            "projects": {
                "type": "array",
                "description": "Two to four concrete things they could build.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "A short, plain name for the project.",
                        },
                        "blurb": {
                            "type": "string",
                            "description": (
                                "One or two sentences on what it does and why it "
                                "suits them. Concrete, not aspirational."
                            ),
                        },
                        "topics": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [c.value for c in Concept],
                            },
                            "description": "Which topics building it would teach.",
                        },
                    },
                    "required": ["title", "blurb", "topics"],
                },
            },
        },
        "required": ["interests", "topics", "projects"],
    },
}

#: The opening line, shown by the web app without calling the model. A greeting
#: costs a round trip and some money to generate and would say the same thing
#: every time, so it is written here and the model is only paid to answer.
WELCOME_GREETING = (
    "Hey — before you dive in, I'd love to know a bit about you.\n\n"
    "What do you spend your time on outside of this? Work, hobbies, anything "
    "you're into. I'm asking because the best thing to build first is almost "
    "always something you already care about."
)


def _welcome_system(learner: "LearnerBrief | None") -> str:
    system = _WELCOME_SYSTEM
    if learner is not None and not learner.is_empty():
        # What they typed on the form a moment ago. Without this the first
        # question would ask something they have just finished answering, which
        # reads as nobody having looked.
        system += "\n\n" + "\n".join(
            ["They already told us this when they signed up:", *_learner_facts(learner)]
        )
    return system


def _read_welcome(response) -> tuple[str, dict | None]:
    reply = "".join(block.text for block in response.content if block.type == "text")
    plan = next(
        (
            block.input
            for block in response.content
            if block.type == "tool_use" and block.name == "record_plan"
        ),
        None,
    )
    if not reply:
        # It recorded a plan but said nothing. Rare, and silence in a chat reads
        # as a bug, so give it something to say.
        reply = (
            "Got it — I've jotted some of that down. Anything else you're "
            "curious about?"
        )
    return reply, plan


def welcome_chat_stream(learner: "LearnerBrief | None", history: list[dict]):
    """The signup conversation, streamed. Same event shape as `chat_stream`.

    Worth streaming even more than the tutor is: this sits in the middle of
    signing up, where a multi-second pause with nothing moving is the moment
    someone decides the thing is broken and closes the tab.

    Terminal event is ``("done", {"reply": str, "plan": dict | None})``.
    """
    try:
        with _client().messages.stream(
            model=settings.anthropic_model,
            max_tokens=_CHAT_MAX_TOKENS,
            system=_welcome_system(learner),
            tools=[_RECORD_PLAN_TOOL],
            messages=history,
            output_config={"effort": "low"},
        ) as stream:
            yield from _pump(stream)
            final = stream.get_final_message()
    except Exception:  # noqa: BLE001 -- external dependency; never crash signup
        logger.exception("welcome chat stream failed")
        yield ("error", "Sorry — I lost my train of thought there. Could you say that again?")
        return

    reply, plan = _read_welcome(final)
    yield ("done", {"reply": reply, "plan": plan})


def welcome_chat(
    learner: "LearnerBrief | None", history: list[dict]
) -> tuple[str, dict | None]:
    """One turn of the signup conversation. Returns (reply, plan | None).

    The plan comes back only on turns where the model chose to record one, and
    the caller persists it. As with chat() above, any failure reaching the model
    degrades to something friendly -- this sits in the middle of signing up, and
    a 500 here loses the account, not just the message.
    """
    try:
        response = _client().messages.create(
            model=settings.anthropic_model,
            max_tokens=_CHAT_MAX_TOKENS,
            system=_welcome_system(learner),
            tools=[_RECORD_PLAN_TOOL],
            messages=history,
            output_config={"effort": "low"},
        )
    except Exception:  # noqa: BLE001 -- external dependency; never crash signup
        logger.exception("welcome chat call failed")
        return (
            "Sorry — I lost my train of thought there. Could you say that again?",
            None,
        )

    return _read_welcome(response)


def _ask_model(
    concept: str,
    focus: str,
    title: str,
    feedback: str | None,
    learner: "LearnerBrief | None" = None,
) -> dict:
    user = (
        f"Build a beginner practice exercise on the concept '{concept}'.\n"
        f"Working title: {title}\n"
        f"It should specifically drill: {focus}\n"
    )
    if learner is not None and not learner.is_empty():
        # The strongest reason to have asked at all: an exercise about the thing
        # they said they wanted to build is the concrete, engaging framing this
        # whole project is a bet on. The concept still rules -- a learner who
        # wants to build a game does not get a worse lesson on dictionaries.
        user += (
            "\nThe learner told us this about themselves when they signed up. "
            "Use it for the SETTING and the data -- what the exercise is about "
            "-- never to change which concept is taught or how hard it is.\n"
        )
        if learner.experience:
            user += f"- Experience when they started: {learner.experience}\n"
        if learner.goals:
            user += f"- What they want to be able to do: {learner.goals[:500]}\n"
        if learner.project_ideas:
            user += f"- What they'd like to build: {learner.project_ideas[:500]}\n"
    if feedback:
        user += (
            "\nYour previous attempt was rejected by the automated check:\n"
            f"{feedback}\nFix it and return a corrected exercise."
        )
    response = _client().messages.create(
        model=settings.anthropic_model,
        max_tokens=_GEN_MAX_TOKENS,
        system=_GEN_SYSTEM,
        messages=[{"role": "user", "content": user}],
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": _EXERCISE_SCHEMA},
        },
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        raise GenerationError("the model returned nothing")
    return json.loads(text)


# ---------------------------------------------------------------------------
# Solving on demand -- the "show me the answer" button
# ---------------------------------------------------------------------------
#
# The ladder deliberately stops before the answer, but a student can now ask to
# see it outright. Solutions aren't stored anywhere (the reference `_solution` is
# stripped before an exercise reaches the database), so we solve the exercise
# fresh and VERIFY it against the exercise's real tests -- including hidden ones --
# before showing it. A student who asks for the answer gets a working answer, not
# the model's best guess. Verified solutions are cached per exercise so repeated
# clicks (and other students) don't re-pay for the same solve.

_SOLUTION_CACHE: dict[str, str] = {}

_SOLVE_SYSTEM = """\
You are showing a beginner the worked answer to a Python exercise they've chosen \
to reveal. Return ONLY the complete, runnable solution code -- the function \
definition(s) that solve it -- and nothing else: no explanation, no commentary, \
no Markdown fences. Write it clean, idiomatic, and beginner-readable, the way a \
good teacher would write the model answer. It must define the named function and \
pass the exercise's tests.\
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        # Drop an opening ```python / ``` line and the closing fence.
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip() + "\n"


def solve(exercise_id: str, entrypoint: str, prompt_md: str, tests: list) -> str:
    """Return a verified worked solution for an exercise.

    Raises GenerationError if the tutor is off or a passing solution can't be
    produced -- the caller turns that into a gentle note, never a broken reveal.
    """
    if not enabled():
        raise GenerationError("the tutor is not switched on")
    if exercise_id in _SOLUTION_CACHE:
        return _SOLUTION_CACHE[exercise_id]

    runner = get_runner()
    feedback: str | None = None
    last_error = "unknown"

    for _ in range(_MAX_GEN_ATTEMPTS):
        user = (
            f"Solve this exercise. The function to define is `{entrypoint}`.\n\n"
            f"{prompt_md.strip()}"
        )
        if feedback:
            user += (
                "\n\nYour previous answer did not pass the tests: "
                f"{feedback}\nReturn a corrected solution."
            )
        try:
            response = _client().messages.create(
                model=settings.anthropic_model,
                max_tokens=1500,
                system=_SOLVE_SYSTEM,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": "medium"},
            )
            code = _strip_fences(
                next((b.text for b in response.content if b.type == "text"), "")
            )
            if not code.strip():
                raise GenerationError("the model returned no code")
            verdict = runner.run(code, entrypoint, tests)
            if not verdict.get("passed"):
                raise GenerationError(f"answer failed the tests: {verdict.get('summary')}")
        except GenerationError as exc:
            last_error = str(exc)
            feedback = last_error
            logger.info("tutor solve attempt rejected: %s", last_error)
            continue
        except Exception:  # noqa: BLE001 -- external call; retry, don't crash
            logger.exception("tutor solve call failed")
            last_error = "the model call failed"
            feedback = last_error
            continue

        _SOLUTION_CACHE[exercise_id] = code
        return code

    raise GenerationError(last_error)


def generate_exercise(
    concept: str,
    focus: str,
    title: str,
    created_by_user_id: str | None = None,
    parent_exercise_id: str | None = None,
    learner: "LearnerBrief | None" = None,
) -> dict:
    """Build and VERIFY a practice exercise, returning a dict ready for
    `Exercise(**spec)`. Raises GenerationError if a sound one can't be produced.

    `created_by_user_id` and `parent_exercise_id` make the result the student's
    own branch off the lesson they were on, rather than a global exercise -- see
    the columns on Exercise.

    Verification is the whole point: the reference solution is run through the
    same harness that grades students, so a broken exercise is caught here rather
    than by the student it was meant to help.
    """
    if not enabled():
        raise GenerationError("the tutor is not switched on")

    concept_enum = Concept(concept)
    runner = get_runner()
    feedback: str | None = None
    last_error = "unknown"

    for _ in range(_MAX_GEN_ATTEMPTS):
        try:
            data = _ask_model(concept, focus, title, feedback, learner)
            entrypoint = str(data["entrypoint"]).strip()
            if not _IDENTIFIER.match(entrypoint):
                raise GenerationError("entrypoint is not a valid function name")
            tests = _validate_tests(data["tests_json"])
            solution = str(data["reference_solution"])

            verdict = runner.run(solution, entrypoint, tests)
            if not verdict.get("passed"):
                raise GenerationError(
                    "the reference solution failed its own tests: "
                    f"{verdict.get('summary')}"
                )
        except (GenerationError, KeyError, ValueError) as exc:
            last_error = str(exc)
            feedback = last_error
            logger.info("tutor generation attempt rejected: %s", last_error)
            continue
        except Exception:  # noqa: BLE001 -- the external call; retry, don't crash
            logger.exception("tutor generation call failed")
            last_error = "the model call failed"
            feedback = last_error
            continue

        slug = f"ai-{concept}-{uuid.uuid4().hex[:8]}"
        return {
            "slug": slug,
            "title": str(data["title"])[:200] or title,
            "theme": Theme.GENERIC,
            "concept": concept_enum,
            "variant": ThemeVariant.GENERIC,
            # No twin: pair_id = slug keeps UNIQUE(pair_id, variant) satisfied.
            "pair_id": slug,
            "entrypoint": entrypoint,
            "prompt_md": str(data["prompt_md"]),
            "starter_code": str(data["starter_code"]),
            "tests": tests,
            "hints": {
                "2": str(data["hint_l2"]),
                "3": str(data["hint_l3"]),
                "4": str(data["hint_l4"]),
            },
            "hint_thresholds": {
                "l2_after_failures": 2,
                "l3_after_failures": 4,
                "l4_after_failures": 6,
                "l2_after_idle_seconds": 300,
            },
            # High so AI-built practice sorts after the taught curriculum.
            "order_index": 9000,
            "created_by_user_id": created_by_user_id,
            "parent_exercise_id": parent_exercise_id,
        }

    raise GenerationError(last_error)
