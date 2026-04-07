from pydantic import BaseModel, ConfigDict, computed_field
from typing import Optional
from datetime import datetime
from typing import List


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

