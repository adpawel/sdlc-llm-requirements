from pydantic import BaseModel, Field
from enum import Enum

class VersionMode(str, Enum):
    human = "human"
    llm = "llm"
    hybrid = "hybrid"

class CaseStudy(str, Enum):
    appointment_booking = "appointment-booking"
    helpdesk_ticketing = "helpdesk-ticketing"
    file_storage_api = "file-storage-api"

class Role(BaseModel):
    name: str
    permissions: list[str]

class FunctionalRequirement(BaseModel):
    id: str = Field(pattern=r"^FR[0-9]+$")
    description: str

class NonFunctionalRequirement(BaseModel):
    id: str = Field(pattern=r"^NFR[0-9]+$")
    description: str

class UserStory(BaseModel):
    id: str = Field(pattern=r"^US[0-9]+$")
    description: str

class AcceptanceCriteria(BaseModel):
    id: str = Field(pattern=r"^AC[0-9]+$")
    given: str
    when: str
    then: str

class ClassificationMetrics(BaseModel):
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1_score: float = Field(ge=0, le=1)


# Task 1
class AmbiguityDetecionMetrics(BaseModel):
    correctness: int = Field(ge=0, le=3)
    completeness: int = Field(ge=0, le=3)
    ambiguity_detection: ClassificationMetrics

# Task 2
class RefinementMetrics(BaseModel):
    quality: int = Field(ge=0, le=3)
    acceptance_criteria_accuracy : int = Field(ge=0, le=3)
    clarity: int = Field(ge=0, le=3)

# Task 3
class ConflictDetectionMetrics(BaseModel):
    correctness: int = Field(ge=0, le=3)
    consistency: int = Field(ge=0, le=3)
    ambiguity_detection: ClassificationMetrics

class Score(BaseModel):
    correctness: int = Field(ge=0, le=3)
    completeness: int = Field(ge=0, le=3)
    consistency: int = Field(ge=0, le=3)
    clarity: int = Field(ge=0, le=3)
    maintainability: int = Field(ge=0, le=3) # to może być metryka stosowana do zbiorowej oceny całego requirements schema 

class ArtifactMetadata(BaseModel):
    version: VersionMode
    case_study: CaseStudy
    model_used: str | None = None
    prompt_log: str | None = None
    human_changes: str | None = None
    score: Score | None = None

class RequirementsArtifact(BaseModel):
    system_goal: str
    roles: list[Role]
    functional_requirements: list[FunctionalRequirement]
    non_functional_requirements: list[NonFunctionalRequirement]
    user_stories: list[UserStory]
    acceptance_criteria: list[AcceptanceCriteria]
    metadata: ArtifactMetadata