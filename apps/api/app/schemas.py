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

from .models import Concept, Role, RunMode, Theme, ThemeVariant


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


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    role: Role
    consented_at: datetime | None
    consent_withdrawn_at: datetime | None
    created_at: datetime


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
