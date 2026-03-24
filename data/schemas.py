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



