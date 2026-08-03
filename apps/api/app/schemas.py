"""API request/response shapes.

Note what is deliberately absent: no schema here ever exposes an Exercise's
hidden test `args`/`expected`, and none exposes hint content above the level the
student has actually unlocked. Those omissions are enforced in the routers, but
they start here -- a response model that cannot represent a leaked answer cannot
leak one by accident.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from typing import Literal

from .models import (
    ONBOARDING_EXPERIENCE,
    Concept,
    Role,
    RunMode,
    Theme,
    ThemeVariant,
)


# --- auth ------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    # 8 is the floor. The 72-byte ceiling is bcrypt's -- it silently truncates
    # beyond that, so a 100-character passphrase would have its tail ignored and
    # the user would never know their password is weaker than they think.
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=120)

    # Study consent. Defaults to False, and the platform works either way -- see
    # the note on User.consented_at about why this must never gate access.
    consent_to_research: bool = False

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        # Without this, "Ben@X.com" and "ben@x.com" become two accounts, and the
        # second signup fails confusingly at the uniqueness check on the first.
        return value.strip().lower()

    @field_validator("display_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Please enter a name we can call you.")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DemoRequest(BaseModel):
    """Which flavour of demo to mint.

    False drops you into a lesson with a clean slate; True hands you an account
    that already has a few days of work, so the dashboard and portfolio have
    something to show.
    """

    with_progress: bool = False


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    role: Role
    consented_at: datetime | None
    consent_withdrawn_at: datetime | None
    created_at: datetime
    #: True for the throwaway accounts behind the landing page's demo buttons.
    #: The app uses it to say so on screen -- letting someone work for twenty
    #: minutes in an account that quietly evaporates is worth avoiding.
    is_demo: bool = False


# --- the second step of signing up ------------------------------------------


class LearnerProfileIn(BaseModel):
    """Answers to the welcome step, or a later edit of part of them.

    Every field is `None` by default, meaning **leave this one as it is** --
    which is not the same as sending `""`, meaning *clear it*. The distinction
    matters because the account page can edit goals and project ideas but cannot
    even read the experience answer: if omitting a field wiped it, saving a new
    goal from that page would silently destroy the thing the tutor uses to pitch
    its explanations, and nothing would show that it had happened.

    The welcome step sends all four, including empty ones when it is skipped.
    """

    goals: str | None = Field(default=None, max_length=2000)
    experience: str | None = Field(default=None, max_length=32)
    experience_note: str | None = Field(default=None, max_length=1000)
    project_ideas: str | None = Field(default=None, max_length=2000)

    @field_validator("experience")
    @classmethod
    def known_experience(cls, value: str | None) -> str | None:
        # An unrecognised key would sail through to the tutor and be described
        # to the model as a level it has never heard of.
        if value and value not in ONBOARDING_EXPERIENCE:
            raise ValueError("unknown experience option")
        return value


class LearnerProfileOut(BaseModel):
    """What comes back out -- and the enforcement point for what does not.

    `experience` and `experience_note` are absent on purpose. The learner is
    asked how much programming they have done so the tutor can pitch itself
    correctly; that answer is not read back to them, so there is no schema here
    capable of returning it. Same principle as the hidden test cases at the top
    of this file: a response model that cannot represent the field cannot leak
    it by accident.
    """

    model_config = ConfigDict(from_attributes=True)

    goals: str
    project_ideas: str
    #: False before the step has been done once, so the web app knows whether to
    #: send a new account to the welcome page.
    completed: bool


class ConsentUpdate(BaseModel):
    """Grant or withdraw study consent, at any time, from the account page.

    Withdrawal must be as easy as granting. If it takes an email to a
    researcher, the right to withdraw exists on paper only.
    """

    consent_to_research: bool


# --- exercises -------------------------------------------------------------


class TestOut(BaseModel):
    """A test as shown to the student.

    Hidden tests appear here with args/expected stripped -- the student learns
    that the test exists and whether it passed, but not what it checks. Hidden
    tests exist to stop hardcoding, not to be mysterious.
    """

    name: str
    hidden: bool
    args: str | None = None
    expected: str | None = None


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    theme: Theme
    concept: Concept
    variant: ThemeVariant
    prompt_md: str
    starter_code: str
    entrypoint: str
    # Visible tests only, and only their shape.
    tests: list[TestOut]


class ExerciseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    theme: Theme
    concept: Concept
    variant: ThemeVariant
    order_index: int


# --- sessions & submissions ------------------------------------------------


class SessionStartResponse(BaseModel):
    session_id: str
    started_at: datetime


class SubmitRequest(BaseModel):
    exercise_id: str
    session_id: str
    code: str
    run_mode: RunMode
    # Present only when run_mode == RUN: the browser harness's own verdict.
    # The server does not trust this for grading -- it is recorded so that a
    # later SUBMIT of identical code can be compared against it and any
    # disagreement flagged. See docs/architecture.md, "The divergence rule".
    client_results: dict | None = None


class SubmitResponse(BaseModel):
    submission_id: str
    passed: bool
    test_results: dict
    # Populated once the Week 4 translator lands; null before that.
    translated_error: str | None = None
    hint_level: int
    hint: str | None = None
    attempt_number: int


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    exercise_id: str
    passed: bool
    run_mode: RunMode
    max_hint_level: int
    seconds_since_exercise_start: int
    attempt_number: int
    created_at: datetime


# --- drafts ----------------------------------------------------------------


class DraftIn(BaseModel):
    code: str


class DraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exercise_id: str
    code: str
    updated_at: datetime


# --- dashboard -------------------------------------------------------------


class ExerciseProgress(BaseModel):
    id: str
    slug: str
    title: str
    concept: Concept
    theme: Theme
    variant: ThemeVariant
    status: Literal["solved", "in_progress", "not_started"]
    attempts: int
    last_attempt_at: datetime | None


class ConceptProgress(BaseModel):
    concept: str
    solved: int
    total: int


class BranchOut(BaseModel):
    """A practice exercise the tutor built for this student, hanging off the
    lesson they made it from. `parent_slug` is where it's drawn in the sequence."""

    parent_slug: str
    slug: str
    title: str
    status: Literal["solved", "in_progress", "not_started"]


class DashboardOut(BaseModel):
    """Note the absences: no time-on-task, no hint depth.

    Both are Week 7 dependent variables, and showing a participant their own
    values changes the behaviour being measured. See routers/progress.py.
    """

    display_name: str
    role: Role
    solved: int
    total_exercises: int
    total_attempts: int
    concepts: list[ConceptProgress]
    continue_slug: str | None
    exercises: list[ExerciseProgress]
    # This student's AI-built branches, each tagged with the lesson it hangs off.
    branches: list[BranchOut]


# --- reflections -----------------------------------------------------------


class ReflectionIn(BaseModel):
    exercise_id: str | None = None
    what_i_tried: str = ""
    where_i_got_stuck: str = ""
    how_i_fixed_it: str = ""


class ReflectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    exercise_id: str | None
    what_i_tried: str
    where_i_got_stuck: str
    how_i_fixed_it: str
    created_at: datetime
    updated_at: datetime


# --- learning content (the Plan stage) --------------------------------------


class QuizQuestionOut(BaseModel):
    """A question as sent to the browser.

    No correct_index and no explanation: both would let a student read the
    answers out of devtools, turning the quiz into a memory test.
    """

    id: str
    prompt: str
    options: list[str]


class LessonOut(BaseModel):
    id: str
    slug: str
    title: str
    concept: Concept
    body_md: str
    questions: list[QuizQuestionOut]
    completed: bool


class QuizAnswer(BaseModel):
    question_id: str
    chosen_index: int


class QuizGradeRequest(BaseModel):
    answers: list[QuizAnswer]


class QuizResult(BaseModel):
    question_id: str
    correct: bool
    correct_index: int
    explanation: str


class QuizGradeResponse(BaseModel):
    correct: int
    total: int
    results: list[QuizResult]


class ParsonsOut(BaseModel):
    id: str
    prompt: str
    shuffled_lines: list[str]


class ParsonsCheckRequest(BaseModel):
    ordering: list[str]


class ParsonsCheckResponse(BaseModel):
    correct: bool
    # How many lines from the top are right. Says where to think without
    # handing over the arrangement.
    correct_prefix: int
    total_lines: int


# --- portfolio --------------------------------------------------------------


class PortfolioEntry(BaseModel):
    exercise_id: str
    slug: str
    title: str
    theme: Theme
    concept: Concept
    solved_at: datetime | None
    attempts: int
    code: str | None
    reflection: ReflectionOut | None


class PortfolioOut(BaseModel):
    display_name: str
    solved: int
    total_attempts: int
    concepts_touched: list[str]
    entries: list[PortfolioEntry]


# --- instructor analytics ---------------------------------------------------


class StudentRow(BaseModel):
    user_id: str
    display_name: str
    solved: int
    total_exercises: int
    attempts: int
    max_hint_level: int
    needs_help: bool


class CommonError(BaseModel):
    error_type: str
    count: int


class InstructorOut(BaseModel):
    students: list[StudentRow]
    common_errors: list[CommonError]
    total_students: int
    total_submissions: int
    # Non-null only when a run/submit disagreement has been recorded. Should
    # always be zero -- see docs/architecture.md, "The divergence rule".
    divergence_incidents: int


# --- reflection tutor ------------------------------------------------------
#
# The AI tutor is a SEPARATE feature from the private journal. It talks to the
# student about the lesson and their code, gauges how secure they feel, and can
# offer to build a supplementary practice lesson. It never reads the journal --
# see routers/reflections.py for the rule this keeps intact.


class TutorMessage(BaseModel):
    """One saved turn of the tutor conversation, sent back to render the history.

    Output-only, so no length ceiling -- the server is echoing what it stored.
    """

    role: Literal["user", "assistant"]
    content: str


class TutorChatRequest(BaseModel):
    exercise_id: str
    # Just the new user turn. The prior conversation is the server's -- it's
    # persisted per (user, exercise) and reloaded each time, so the browser can't
    # rewrite the history and the chat survives navigating away and back.
    message: str = Field(min_length=1, max_length=8000)


class LessonProposal(BaseModel):
    """The tutor's offer to build more practice.

    `scope` distinguishes "more of this whole topic" from "a specific thing I
    noticed you wobble on" -- exactly the two the brief asks for.
    """

    scope: Literal["topic", "concept"]
    concept: Concept
    focus: str = Field(max_length=400)
    title: str = Field(max_length=120)
    rationale: str = Field(max_length=600)


class TutorChatResponse(BaseModel):
    reply: str
    # Present only when the tutor offered to build a lesson this turn. The
    # student accepts it explicitly; nothing is generated without a click.
    proposal: LessonProposal | None = None
    # False when no API key is configured. The UI uses this to show a gentle
    # "not switched on yet" note instead of pretending the tutor is thinking.
    configured: bool = True


class GenerateLessonRequest(BaseModel):
    concept: Concept
    focus: str = Field(min_length=1, max_length=400)
    title: str = Field(min_length=1, max_length=120)
    # The lesson the student was on when they asked for this -- the branch's
    # parent. The tutor always knows it, so it's required.
    parent_exercise_id: str


class GeneratedLessonResponse(BaseModel):
    """A freshly built, harness-verified practice exercise the student can open."""

    slug: str
    title: str


class BranchLink(BaseModel):
    """One AI-built branch off an exercise, for the parent's own page."""

    slug: str
    title: str
    status: Literal["solved", "in_progress", "not_started"]


class SolutionResponse(BaseModel):
    """A worked answer, produced on demand and verified against the real tests
    before it is ever sent. The ladder stops before the answer; this is the
    student choosing to step past it."""

    solution: str


class HintRequest(BaseModel):
    """A student pulling a hint on demand, rather than the ladder pushing one."""

    session_id: str


class HintResponse(BaseModel):
    level: int
    hint: str | None
    # True when this is the last rung -- the UI can point to 'Show the answer'.
    exhausted: bool
