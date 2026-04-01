from fastapi import APIRouter, HTTPException, Request, Depends, Response, Query, status
from typing import Optional
#from fastapi.responses import RedirectResponse
from data.models import (
    JobRole,
    Session,
    Answer,
    Question,
)
from data.db import SessionLocal
from data.schemas import (
    RoleAndDescriptionSchema,
    QuestionSchema,
    RoleResponseSchema,
    SessionWithQuestionIdsSchema,
    QuestionAnswersSchema,
    AnswerSchema,
    SessionResponseSchema,
)
from services.utils import construct_session_response
from services.load_job_descriptions import ai_get_interview_questions_from_description
from services.ai_interview import generate_ai_answer
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

#INTERVIEWING

@router.get("/startinterviewsession", response_model = int)
async def start_interview():
    """
        Starts a session by creating an entry in the sessions table
    """

    try:
        async with SessionLocal() as session:
            session = await Session.create_session(db=session, thread_id=None)
            return session.id
    except Exception as e:
        print("ERROR STARTING THE SESSION",e)
        raise HTTPException(status_code=400,detail="Unable to start session")

@router.post("/askquestions", response_model = SessionResponseSchema)
async def ask_questions(session_and_question_ids : SessionWithQuestionIdsSchema):
    """
        1. Get the questions to ask one by one by the AI
        2. Add the answers
        3. Return the session with the answers 
    """
    #Get the questions

    async with SessionLocal() as session:
        session_exists = await Session.exists(session,session_and_question_ids.session_id)
        print("DOES THE SSIONS EXIST", session_exists)
        if not session_exists:
            raise HTTPException(status_code=404,detail="The session could not be found")
        question_list = await Question.get_by_ids(session,session_and_question_ids.question_ids)
        print("Question List", question_list)
        #Get the answers from OpenAI
        ai_answers = []
        for q in question_list:
            answer = generate_ai_answer(q.question_text)
            ai_answers.append({
                "question_id" : q.id,
                "answer_text" : answer
            })
        print("ANSWERS FROM AI", ai_answers)

        #ai_answers = [{'question_id': 7, 'answer_text': 'In my role supporting the Government of Jersey’s adoption of Microsoft Azure, I was responsible for transforming the high-level security architecture mandated by organizational policy into actionable, technical solutions within the new cloud environment. This included designing and implementing identity and access management, deploying security monitoring, and ensuring secure configurations across multiple domains. One of the key challenges was translating abstract security requirements into Azure-native controls while maintaining compliance and usability for multiple stakeholders. Bridging the gap between policy and platform often required balancing stringent security controls with the flexibility needed for day-to-day operations, and involved close collaboration with cloud engineers, architects, and security specialists to ensure all requirements were met without compromising productivity or performance.'}, {'question_id': 12, 'answer_text': 'When deploying a new security control across multiple environments, I follow a structured and collaborative approach. First, I engage with stakeholders to fully understand the business requirements and ensure that the security objectives align with organizational priorities. Next, I analyze the technical and operational aspects of each environment to tailor the implementation plan, minimizing risks and addressing unique challenges. I coordinate with security architecture and engineering teams, facilitating solution design, documentation, and the necessary security reviews. During the rollout, I manage communications, oversee the deployment process, and monitor progress to identify and resolve any issues promptly. I also ensure thorough documentation and user awareness training to maintain operational effectiveness and compliance across all environments. This approach has proven successful in leading large-scale security transformation projects and global security program rollouts involving various stakeholders and complex infrastructures .'}, {'question_id': 15, 'answer_text': 'To improve the Secure Score of an M365 environment, I would begin by reviewing Microsoft’s recommendations within the Secure Score Dashboard and systematically addressing high-impact security controls. Based on my experience delivering M365 security posture reviews and hardening environments, I would focus on enabling multifactor authentication for all users, strengthening conditional access policies, and ensuring role-based access controls are enforced. I would also review audit logs and configure alerting for suspicious activities, and work to implement secure configuration baselines across Exchange Online, SharePoint Online, and Teams. User awareness and training are also priorities, as I have developed and delivered training for M365 security features to ensure ongoing compliance and user adoption. These targeted actions help drive up the Secure Score while reducing real-world risks.'}]
        interview_session = await Answer.create_answers_bulk(session,session_and_question_ids.session_id,ai_answers)

        session_response = construct_session_response(interview_session)
        print("CREATED SESSION IN DB", interview_session)
        return session_response

    





@router.get("/getrandomquestions", response_model = List[QuestionSchema])
async def get_random_questions(role_id: int = Query(),amount: int | None = Query(None) ):
    """
        Get random questions existing for a job role
    """

    try:
        async with SessionLocal() as session:
            random_questions = await JobRole.get_random_questions(session,role_id,amount)
            question_list_response = [ QuestionSchema.model_validate(q_data) for q_data in random_questions ]
            return question_list_response
    except Exception as e:
        print("ERROR STARTING THE SESSION",e)
        raise HTTPException(status_code=400,detail="Unable to start session")
    

@router.get("/getinterviewsessionbyid", response_model = SessionResponseSchema)
async def get_session_by_id(session_id: int = Query()):
    """
        Get interview session and return an object with questions and answers
    """
    async with SessionLocal() as session:
        interview_session = await Session.get_session_with_questions_and_answers(session,session_id)
        if not interview_session:
            raise HTTPException(status_code=404,detail="Interview session not found")
        
        session_response = construct_session_response(interview_session)
        # question_answers_list: List[QuestionAnswersSchema] = []
        # for answer in interview_session.question_answers:
        #     question_answers_list.append(
        #         QuestionAnswersSchema(
        #             question=answer.question,  # relies on QuestionSchema.from_attributes=True
        #             answers=[
        #                 AnswerSchema(
        #                     id=answer.id,
        #                     answer_text=answer.answer_text,
        #                     added_at=answer.added_at
        #                 )
        #             ]
        #         )
        #     )

        # session_response = SessionResponseSchema(
        #     id=interview_session.id,
        #     question_answers=question_answers_list
        # )

        print("SESSION FOUND", session_response)
        return session_response
