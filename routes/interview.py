from fastapi import APIRouter, HTTPException, Request, Depends, Response, Query, status
from typing import Optional
#from fastapi.responses import RedirectResponse
from data.models import (
    JobRole
)
from data.db import SessionLocal
from data.schemas import (
    RoleAndDescriptionSchema,
    QuestionSchema,
    RoleResponseSchema
)
from services.load_job_descriptions import ai_get_interview_questions_from_description
from typing import List
from pathlib import Path
import json
import os
import bleach
import base64

router = APIRouter()

# Go to project root (adjust parents[n] if needed)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

ALLOWED_REDIRECTS = [
    "uk.chrisbriant.idbroker://callback",
]


@router.post("/createroleandquestionset", response_model = RoleResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_role_and_question_set(role_and_description : RoleAndDescriptionSchema):
    """
        Uses AI to generate an interview question set for a given job role and job description
    """
    print("ROLE TO SEND TO AI", role_and_description.role_description, role_and_description.role_name)

    #Sanitize the feedback input data
    cleaned_role_name = bleach.clean(role_and_description.role_name, tags=[], attributes={}, strip=True)
    cleaned_role_description = bleach.clean(role_and_description.role_description, tags=[], attributes={}, strip=True)
    #TODO : Send this to the AI and get the JSON RESPONSE STORE IN DB
    interview_questions = ai_get_interview_questions_from_description(cleaned_role_description,cleaned_role_name)
    try: 
        async with SessionLocal() as session:
            role = await JobRole.create_from_ai_json(
                db=session,
                data=interview_questions
            )
            questions_list = [
                    QuestionSchema(
                        id=q.id,
                        question_type=q.question_type or "",
                        question_text=q.question_text,
                        created_at=q.created_at,
                        updated_at=q.updated_at
                    )
                    for q in role.questions
            ]

            # Construct RoleResponseSchema for each role
            role_data = RoleResponseSchema(
                id=role.id,
                role_name=role.role_name,
                role_text=role.role_text,
                questions=questions_list
            )
            return role_data
    except Exception as e:
        print("Error adding to database", e)
        raise HTTPException(status_code=400,detail="Unable to generate role data")


@router.get("/getroleswithquestions", response_model = List[RoleResponseSchema])
async def get_roles_with_questions():
    try:
        async with SessionLocal() as session:
            roles = await JobRole.get_all_roles(db=session)
            print("HERE ARE ALL THE ROLES", roles)
            role_schema_response = []
            for role in roles:
                questions_list = [
                    QuestionSchema(
                        id=q.id,
                        question_type=q.question_type or "",
                        question_text=q.question_text,
                        created_at=q.created_at,
                        updated_at=q.updated_at
                    )
                    for q in role.questions
                ]

                # Construct RoleResponseSchema for each role
                role_data = RoleResponseSchema(
                    id=role.id,
                    role_name=role.role_name,
                    role_text=role.role_text,
                    questions=questions_list
                )

                role_schema_response.append(role_data)
            print("RESPONSE DATA", role_schema_response)
            return role_schema_response
    except Exception as e:
        print("ERROR GETTING THE ROLES",e)
        raise HTTPException(status_code=400,detail="Unable to retrieve roles")
