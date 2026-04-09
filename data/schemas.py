from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime
from typing import List, TypeVar, Optional, Generic


class RoleAndDescriptionSchema(BaseModel):
    role_name: str
    role_description : str

class QuestionSchema(BaseModel):
    id : int
    question_type : str
    question_text : str
    created_at : datetime
    updated_at : datetime

    model_config = ConfigDict(from_attributes=True)


class RoleResponseSchema(BaseModel):
    id: int
    role_name : str
    role_text : str
    questions : List[QuestionSchema]

    model_config = ConfigDict(from_attributes=True)

#Just the role without any questions
class RoleWDescriptionResponseSchema(BaseModel):
    role_name : str
    role_text : str

    model_config = ConfigDict(from_attributes=True)

class SessionWithQuestionIdsSchema(BaseModel):
    session_id : int
    question_ids : List[int]

class AnswerSchema(BaseModel):
    id : int
    answer_text : str
    added_at : datetime

    model_config = ConfigDict(from_attributes=True)

class QuestionAnswersSchema(BaseModel):
    question : QuestionSchema
    answers : List[AnswerSchema]

class SessionResponseSchema(BaseModel):
    id : int
    question_answers : List[QuestionAnswersSchema]

#Just the session with the time started and the role
class SessionRoleResponseSchema(BaseModel):
    id : int
    started_at : datetime
    job_role: RoleWDescriptionResponseSchema | None

    model_config = ConfigDict(from_attributes=True)

class PaginatedSessionResponse(BaseModel):
    data: List[SessionRoleResponseSchema]
    next_page: Optional[str]

#For Generic Pagination
T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    next_page: Optional[str]
    total: int
    total_pages: int
    page: int
    page_size: int

class RoleQuestionAnswerInputSchema(BaseModel):
    session_id : int
    question_id : int
    user_answer : str

class ScoredAnswerSchema(BaseModel):
    scored_answer_id : int
    score : int
    question : QuestionSchema
    suggested_answer : AnswerSchema
    user_answer : AnswerSchema

class ScoredSessionResponseSchema(BaseModel):
    id : int
    scored_answers : List[ScoredAnswerSchema]

class RoleAndSessionResponseSchema(BaseModel):
    role : RoleResponseSchema
    scored_session : ScoredSessionResponseSchema

