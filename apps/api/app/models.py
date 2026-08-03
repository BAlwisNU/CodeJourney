"""Database models.

Design note, and it is the important one: `Submission` is not application
plumbing, it is the research dataset. Every column below either serves the
platform or serves the Week 8 analysis, and several serve only the analysis.
They are here in Week 1 because the alternative -- discovering in Week 7 that
the wrong things were logged -- is the single most common way a project like
this ends up with nothing to write about.

The dependent variables the study needs, and where they come from:

    time-on-task      -> Submission.seconds_since_exercise_start
    completion        -> Submission.passed, first occurrence per (user, exercise)
    hint depth        -> Submission.max_hint_level, and HintEvent for the ladder
    motivation        -> IMI questionnaire, collected out-of-band, joined on user
    condition         -> Submission.theme_variant, via Exercise.pair_id

`Exercise.pair_id` is what makes the within-subjects comparison possible at all:
it links a themed exercise to its generic twin -- same concept, same tests, same
difficulty, different framing. Without it there is no comparison, only two piles
of unrelated exercises.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Role(str, enum.Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"


class Theme(str, enum.Enum):
    """The five worlds, plus GENERIC for the control condition.

    Each theme is tied to a DATA SHAPE, not a set of variable names. See
    docs/theme-concept-grid.md -- a theme that only changes identifiers is the
    documented failure mode of this project, not a shortcut.

    These are concrete, playful domains: things a beginner can picture and wants
    to see working. The comparison the platform tests is engaging concrete
    framing against the same problem stated abstractly -- which is what the
    GENERIC twin is for.
    """

    GAMES = "games"          # records with state -- quests, inventories, scores
    SPORTS = "sports"        # aggregation over groups -- leagues, tallies
    SPACE = "space"          # sequences and journeys -- missions, waypoints
    MUSIC = "music"          # pairings and patterns -- playlists, sets
    STORIES = "stories"      # generation and transformation -- text, word games
    GENERIC = "generic"      # control condition -- the same problem, stated dryly


class Concept(str, enum.Enum):
    LISTS = "lists"
    DICTS = "dicts"
    LOOPS = "loops"
    STRINGS = "strings"
    FUNCTIONS = "functions"
    FILE_IO = "file_io"


class ThemeVariant(str, enum.Enum):
    """The independent variable. This is the whole experiment."""

    THEMED = "themed"
    GENERIC = "generic"


class RunMode(str, enum.Enum):
    """Where the code executed.

    RUN is Pyodide in the browser -- untrusted, instant, not graded.
    SUBMIT is the server sandbox -- trusted, graded, the only thing that counts.
    """

    RUN = "run"
    SUBMIT = "submit"


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.STUDENT)

    # Study bookkeeping. Null until the participant actively opts in; no study
    # data may be analysed without it.
    #
    # Consent is NOT required to use the platform. Making it a condition of
    # access would be coercive -- a student who needs the exercises for their
    # course cannot meaningfully refuse -- and an ethics committee should reject
    # that design. Non-consenting users get the full platform; their rows are
    # simply excluded from analysis.
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set when someone withdraws. Kept as a separate column rather than just
    # nulling consented_at so the audit trail distinguishes "never consented"
    # from "consented, then withdrew" -- the right to withdraw is worthless if
    # exercising it leaves no record that it happened.
    consent_withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    # Which order this participant sees themed/generic in. Counterbalancing is
    # assigned once, at enrolment, and never recomputed -- otherwise the design
    # silently breaks.
    counterbalance_group: Mapped[str | None] = mapped_column(String(1))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")
    reflections: Mapped[list["Reflection"]] = relationship(back_populates="user")
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    learner_profile: Mapped["LearnerProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class LearnerProfile(Base):
    """What the learner told us about themselves at signup.

    Collected on the second step of signing up: what they want to be able to
    do, how much programming they have done, and anything they already want to
    build. All three are optional -- the step can be skipped, and a wall of
    questions between someone and the thing they came for is a good way to lose
    them before they have written a line of code.

    **Who can read what.** `goals` and `project_ideas` come back to the learner
    on their account page and are theirs to edit. `experience` and
    `experience_note` are deliberately not returned by any endpoint; see
    schemas.LearnerProfileOut. Nothing here is exposed to instructors, and
    nothing here is part of the study dataset -- it exists to shape teaching,
    not to be analysed.

    **The tutor reads all of it.** That is the point of collecting it: see the
    note on TutorContext.learner in services/tutor.py. It is a different thing
    from the tried/stuck/fixed journal, which no model ever sees -- this is text
    a learner wrote *in order to* be taught better, and the form says so where
    they write it.

    A separate table rather than columns on `users`, for the same reason as
    OAuthAccount below: it is new, so create_all builds it, and nobody's
    existing database has to be migrated.
    """

    __tablename__ = "learner_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    #: "I want to be able to..." -- free text, in their own words.
    goals: Mapped[str] = mapped_column(Text, default="")
    #: One of ONBOARDING_EXPERIENCE below. Free text would be harder to use and
    #: no more honest; the note beside it catches whatever the options miss.
    experience: Mapped[str] = mapped_column(String(32), default="")
    experience_note: Mapped[str] = mapped_column(Text, default="")
    #: Anything they already want to build. The most useful single field for
    #: making an exercise feel like it is theirs.
    project_ideas: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    user: Mapped["User"] = relationship(back_populates="learner_profile")


class OnboardingMessage(Base):
    """One turn of the welcome conversation -- step three of signing up.

    A chat about what someone is interested in and what they might build, which
    ends with a plan. Persisted so closing the tab mid-conversation doesn't
    throw it away.

    Kept apart from TutorChatMessage even though both are chats with the same
    model: that one is scoped to a single exercise and belongs to the Reflect
    stage, this one has no exercise at all and happens once. Sharing a table
    would mean a nullable exercise_id and every query filtering on it.
    """

    __tablename__ = "onboarding_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    #: "user" or "assistant" -- the two roles the API accepts back as history.
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class OnboardingPlan(Base):
    """What the welcome conversation concluded.

    A separate table from LearnerProfile on purpose, and the distinction is
    worth keeping: LearnerProfile is what the learner *said*, in their own
    words. This is what a model *inferred* from talking to them. Merging the two
    would make it impossible to tell a person's own words from a machine's
    paraphrase of them -- which matters when the thing being stored is "what
    this person wants from their education".

    All of it is theirs to read on their account page, and all of it is offered
    back to the tutor later so a conversation months from now still knows what
    they came for.
    """

    __tablename__ = "onboarding_plans"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    #: A sentence or two on what this person is into, in the model's words.
    interests: Mapped[str] = mapped_column(Text, default="")
    #: Concept keys from the Concept enum, so a suggestion maps onto a topic
    #: that actually exists rather than something invented.
    topics: Mapped[list] = mapped_column(JSON, default=list)
    #: [{"title": str, "blurb": str, "topics": [concept keys]}]
    projects: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


#: The experience options, in the order they are offered. Keys are stored;
#: labels are what the form shows and what the tutor is told.
ONBOARDING_EXPERIENCE: dict[str, str] = {
    "none": "Never written code before",
    "some_python": "Tried a bit of Python before",
    "other_language": "Comfortable in another language, new to Python",
    "rusty": "Learnt some once, but it's rusty",
}


class OAuthAccount(Base):
    """A Google or Microsoft identity linked to a CodeJourney account.

    A separate table rather than two columns on `users`, for two reasons. One
    person can link both providers -- signing up with Google and later hitting
    "Continue with Microsoft" on the same email should log them in, not fail or
    silently overwrite. And because it is a NEW table, `create_all` builds it on
    startup; adding columns to `users` would not have applied to anyone's
    existing database, since this project has no migration tool yet (see the
    note in main.py).

    `subject` is the provider's own immutable user id -- Google's `sub`, not the
    email. Emails get reassigned and renamed; the subject does not, and matching
    on it is what stops a recycled address from inheriting someone's account.
    """

    __tablename__ = "oauth_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(32))
    subject: Mapped[str] = mapped_column(String(255))
    # The address the provider gave us at link time, kept for support questions
    # ("which account did I sign up with?"). Never used to look anyone up.
    email: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="oauth_accounts")

    __table_args__ = (
        # One provider identity maps to exactly one account, forever.
        UniqueConstraint("provider", "subject", name="uq_oauth_provider_subject"),
    )


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))

    theme: Mapped[Theme] = mapped_column(Enum(Theme))
    concept: Mapped[Concept] = mapped_column(Enum(Concept))
    variant: Mapped[ThemeVariant] = mapped_column(Enum(ThemeVariant))

    # Links a themed exercise to its generic twin. Both rows share a pair_id.
    # Same concept, same tests, same entrypoint, same difficulty -- only the
    # framing differs. This column IS the experiment; without it the Week 7 data
    # cannot be analysed within-subjects.
    pair_id: Mapped[str] = mapped_column(String(36), index=True)

    prompt_md: Mapped[str] = mapped_column(Text)
    starter_code: Mapped[str] = mapped_column(Text, default="")

    # Function the tests call. Function-based tests, rather than stdout matching,
    # are what let the same harness run under Pyodide and CPython and agree.
    entrypoint: Mapped[str] = mapped_column(String(80))

    # [{name, args, expected, hidden}] -- consumed directly by packages/harness.
    tests: Mapped[list] = mapped_column(JSON, default=list)

    # Hint ladder content: {"2": "...", "3": "...", "4": "..."}
    # L0/L1 are generated (test output, translated error), L5 is a human.
    hints: Mapped[dict] = mapped_column(JSON, default=dict)

    # Per-exercise ladder thresholds, overriding the defaults in services/hints.py.
    # Configurable per exercise turns the platform into a research instrument:
    # thresholds become a manipulable variable rather than a hardcoded guess.
    # e.g. {"l2_after_failures": 2, "l3_after_failures": 4, "l4_after_failures": 6,
    #       "l2_after_idle_seconds": 300}
    hint_thresholds: Mapped[dict] = mapped_column(JSON, default=dict)

    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Null for the taught curriculum, which everyone sees. Set for a practice
    # exercise the AI tutor built for one student -- their own branch, visible
    # only to them. This is what keeps a generated lesson from cluttering every
    # other student's dashboard.
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    # The exercise this one was branched from -- the lesson the student was on
    # when they asked for more practice. Drives where the branch is drawn in the
    # dashboard sequence: hanging off its parent.
    parent_exercise_id: Mapped[str | None] = mapped_column(
        ForeignKey("exercises.id"), index=True
    )

    __table_args__ = (
        # A pair has at most one themed and one generic side.
        UniqueConstraint("pair_id", "variant", name="uq_exercise_pair_variant"),
        Index("ix_exercise_concept_variant", "concept", "variant"),
    )


# ---------------------------------------------------------------------------
# Attempts
# ---------------------------------------------------------------------------


class ExerciseSession(Base):
    """One sitting at one exercise.

    Exists to make time-on-task measurable. `started_at` is stamped when the
    exercise is opened, so `seconds_since_exercise_start` on each submission is
    a real elapsed time rather than a guess reconstructed from timestamps.
    """

    __tablename__ = "exercise_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), index=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    # Set when the student first passes, or abandons. Null = still open.
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_session_user_exercise", "user_id", "exercise_id"),)


class Submission(Base):
    """THE research dataset. Add columns here reluctantly; remove them never.

    One row per Submit. Run (Pyodide) events are logged too, with
    run_mode=RUN and passed reflecting the browser harness -- they are the
    iteration signal, and excluding them would hide most of the learning
    behaviour. Only run_mode=SUBMIT rows are authoritative for grading.
    """

    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), index=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("exercise_sessions.id"), index=True
    )

    code: Mapped[str] = mapped_column(Text)
    run_mode: Mapped[RunMode] = mapped_column(Enum(RunMode))

    # Denormalised from Exercise on purpose. The condition a submission was made
    # under must be frozen at write time: if an exercise is ever re-themed or
    # re-paired mid-study, joining through Exercise at analysis time would
    # silently rewrite history.
    theme_variant: Mapped[ThemeVariant] = mapped_column(Enum(ThemeVariant))

    # Full harness output: {phase, error, stdout, tests[], passed, summary}.
    test_results: Mapped[dict] = mapped_column(JSON, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Highest hint level revealed for this exercise at the moment of submitting.
    # Feeds the mastery penalty term and is a dependent variable in its own right.
    max_hint_level: Mapped[int] = mapped_column(Integer, default=0)

    # Elapsed seconds since ExerciseSession.started_at. Computed server-side --
    # never trust a client clock for a measured variable.
    seconds_since_exercise_start: Mapped[int] = mapped_column(Integer, default=0)

    attempt_number: Mapped[int] = mapped_column(Integer, default=1)

    # Set when Run and Submit disagree on the same code. Should always be false.
    # If this is ever true in the dataset it is a platform incident and those
    # rows need flagging before analysis. See docs/architecture.md.
    divergence_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )

    user: Mapped[User] = relationship(back_populates="submissions")

    __table_args__ = (
        Index("ix_submission_user_exercise_time", "user_id", "exercise_id", "created_at"),
        Index("ix_submission_variant", "theme_variant"),
    )


# ---------------------------------------------------------------------------
# Learning content -- the "Plan" stage of Connect > Plan > Create > Test > Reflect
# ---------------------------------------------------------------------------


class Lesson(Base):
    """A short teaching page for one concept.

    Keyed by concept rather than by exercise, so the same lesson serves every
    exercise on that concept -- including both sides of a themed/generic pair.
    That matters for the study: if the themed exercise had a richer lesson than
    its twin, the comparison would measure teaching quality, not framing.
    """

    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    concept: Mapped[Concept] = mapped_column(Enum(Concept), index=True)

    body_md: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )


class QuizQuestion(Base):
    """A multiple-choice check on the lesson.

    `explanation` is shown after answering, for right and wrong answers alike --
    a student who guessed correctly still needs to know why, and one who got it
    wrong needs more than a red cross.
    """

    __tablename__ = "quiz_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), index=True)

    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON, default=list)
    correct_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    lesson: Mapped[Lesson] = relationship(back_populates="questions")


class ParsonsProblem(Base):
    """Drag the shuffled lines into the right order.

    The stepping stone between reading a worked example and facing an empty
    editor: the student reasons about structure and order without also having to
    fight syntax. Cheap to build, and well-evidenced (Denny et al.).

    `lines` is the correct solution in order. `distractors` are plausible wrong
    lines mixed in -- optional, because they raise difficulty sharply and are
    wrong for a first encounter with a concept.
    """

    __tablename__ = "parsons_problems"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), index=True)

    prompt: Mapped[str] = mapped_column(Text, default="")
    lines: Mapped[list] = mapped_column(JSON, default=list)
    distractors: Mapped[list] = mapped_column(JSON, default=list)


class LessonProgress(Base):
    """Which lessons a student has worked through, and how the quiz went."""

    __tablename__ = "lesson_progress"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), index=True)

    quiz_correct: Mapped[int] = mapped_column(Integer, default=0)
    quiz_total: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress"),
    )


class ParsonsAttempt(Base):
    """One check of a Parsons ordering.

    Recorded per attempt rather than as a flag, because "how many goes did the
    warm-up take" is a cheap signal of whether the concept landed before they
    ever opened the editor.
    """

    __tablename__ = "parsons_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    problem_id: Mapped[str] = mapped_column(
        ForeignKey("parsons_problems.id"), index=True
    )

    correct: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Draft(Base):
    """Work in progress. One row per (user, exercise), overwritten as they type.

    NOT part of the research dataset. A draft is convenience state -- it exists
    so a refresh, a closed laptop, or a switch to the phone doesn't destroy
    someone's work. `Submission` remains the only record of what was actually
    attempted, and nothing here should ever be analysed.

    Deliberately does NOT touch ExerciseSession.last_activity_at. That field
    drives the idle-based L2 hint trigger, and letting autosave update it would
    silently change when hints appear -- a study variable quietly altered by an
    unrelated convenience feature. See services/hints.py.
    """

    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), index=True)

    code: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    __table_args__ = (
        UniqueConstraint("user_id", "exercise_id", name="uq_draft_user_exercise"),
    )


class HintEvent(Base):
    """One row per hint reveal. The ladder's audit trail.

    Separate from Submission because hints are triggered by idle time as well as
    by failed attempts, so they don't map one-to-one onto submissions.
    """

    __tablename__ = "hint_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("exercise_sessions.id"))

    level: Mapped[int] = mapped_column(Integer)
    # "failures" | "idle" | "requested" -- did the ladder push, or did they pull?
    # A student who always pulls L4 immediately is a different phenomenon from
    # one the system escalated, and the report will want to tell them apart.
    trigger: Mapped[str] = mapped_column(String(20))

    failures_at_trigger: Mapped[int] = mapped_column(Integer, default=0)
    seconds_at_trigger: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ---------------------------------------------------------------------------
# Reflection
# ---------------------------------------------------------------------------


class Reflection(Base):
    """The learning journal.

    HARD RULE, enforced structurally rather than by policy: reflection text is
    never sent to an LLM, and no service outside this module may read `body`
    except to render it back to its author or to an instructor with access.

    A student writing about "personal growth and challenges" may disclose real
    distress. The proposal promises the system makes no psychological
    judgements; keeping the AI's eyes on code only is what makes that promise
    structural instead of aspirational. There is deliberately no
    `sentiment`, `flags`, or `summary` column here -- adding one would be the
    first step toward breaking that guarantee.
    """

    __tablename__ = "reflections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    exercise_id: Mapped[str | None] = mapped_column(ForeignKey("exercises.id"))

    what_i_tried: Mapped[str] = mapped_column(Text, default="")
    where_i_got_stuck: Mapped[str] = mapped_column(Text, default="")
    how_i_fixed_it: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    user: Mapped[User] = relationship(back_populates="reflections")


class TutorChatMessage(Base):
    """One saved turn of the reflection tutor conversation.

    Persisted per (user, exercise) so the chat comes back exactly as the student
    left it when they return to that lesson's Reflect page.

    This is the TUTOR conversation, which already goes to an LLM by design. It is
    a DIFFERENT thing from the private tried/stuck/fixed journal (`Reflection`),
    which never touches an LLM and has no `sentiment`/`summary` columns. They live
    in separate tables on purpose -- so the wall between "the AI may see this" and
    "the AI never sees this" stays obvious in the schema itself. Nothing here is
    read by any service other than the tutor rendering it back to its author.
    """

    __tablename__ = "tutor_chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), index=True)

    # "user" | "assistant" -- the two roles the visible conversation has. The
    # greeting is drawn client-side and never stored.
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_tutor_chat_user_exercise_time", "user_id", "exercise_id", "created_at"),
    )


class Mastery(Base):
    """Per-concept mastery score. Deliberately simple and explainable.

        score = sum(w_i * pass_i * penalty_i) / sum(w_i)
          w_i       = recency weight, decays with attempt age
          penalty_i = 1 / (1 + 0.3 * max_hint_level)

    Thresholds: <0.4 remediate, 0.4-0.75 practice, >0.75 advance.

    Stored rather than computed on read so the instructor dashboard doesn't
    recompute over every submission on every page load. Recomputed on each
    graded submit -- see services/mastery.py.
    """

    __tablename__ = "mastery"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    concept: Mapped[Concept] = mapped_column(Enum(Concept))

    score: Mapped[float] = mapped_column(Float, default=0.0)
    attempts_counted: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    __table_args__ = (
        UniqueConstraint("user_id", "concept", name="uq_mastery_user_concept"),
    )
