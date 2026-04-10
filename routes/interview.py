from fastapi import APIRouter, HTTPException, Request, Depends, Response, Query, status
from typing import Optional
#from fastapi.responses import RedirectResponse
from data.models import (
    JobRole,
    Session,
    Answer,
    Question,
    QuestionType,
    ScoredAnswer,
)
from data.db import SessionLocal
from data.schemas import (
    RoleAndDescriptionSchema,
    QuestionSchema,
    RoleAndQuestionSetInputSchema,
    RoleResponseSchema,
    SessionWithQuestionIdsSchema,
    QuestionAnswersSchema,
    AnswerSchema,
    SessionResponseSchema,
    RoleQuestionAnswerInputSchema,
    ScoredAnswerSchema,
    ScoredSessionResponseSchema,
    RoleAndSessionResponseSchema,
    SessionRoleResponseSchema,
    RoleWDescriptionResponseSchema,
    PaginatedSessionResponse,
    PaginatedResponse,
)
from services.utils import construct_session_response
from services.load_job_descriptions import ai_get_interview_questions_from_description
from services.ai_interview import generate_ai_answer, get_score_and_suggested_answer
from typing import List
from pathlib import Path
import json
import os
import bleach
import base64
from math import ceil
from services.auth import get_api_key

router = APIRouter()

# Go to project root (adjust parents[n] if needed)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ALLOWED_REDIRECTS = [
#     "uk.chrisbriant.idbroker://callback",
# ]


@router.post("/createroleandquestionset", response_model = RoleResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_role_and_question_set(role_and_description : RoleAndDescriptionSchema, api_key: str = Depends(get_api_key)):
    """
        Uses AI to generate an interview question set for a given job role and job description
    """
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


@router.post("/createrole", response_model = RoleResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_role(role_and_description : RoleAndDescriptionSchema, api_key: str = Depends(get_api_key)):
    """
        Create a role without generating the questions
    """
    #Sanitize the feedback input data
    cleaned_role_name = bleach.clean(role_and_description.role_name, tags=[], attributes={}, strip=True)
    cleaned_role_description = bleach.clean(role_and_description.role_description, tags=[], attributes={}, strip=True)
    try: 
        async with SessionLocal() as session:
            role = await JobRole.create_from_ai_json(
                db=session,
                data={
                    "role_name" : cleaned_role_name,
                    "role_text" : cleaned_role_description,
                }
            )
            role_data = RoleResponseSchema(
                id=role.id,
                role_name=role.role_name,
                role_text=role.role_text,
                questions=[]
            )
            return role_data
    except Exception as e:
        print("Error adding to database", e)
        raise HTTPException(status_code=400,detail="Unable to generate role data")


@router.post("/addquestionstorole", response_model = RoleResponseSchema, status_code=status.HTTP_201_CREATED)
async def add_questions_to_role(role_question_set : RoleAndQuestionSetInputSchema , api_key: str = Depends(get_api_key)):
    """
        Add questions to a role
        role_id : integer
        question_set : List of questions 
            question_text : the question itself str
            type : str - must be of "technical", "architecture", "scenario" or "behavioural"
    """
    #Get the accepted question types
    valid_question_types = [ qt.value for qt in list(QuestionType) ]
    print(valid_question_types)
    #Prepare the question list as cleaned text from the input
    cleaned_questions = {
        "technical_questions" : [],
        "architecture_questions" : [],
        "scenario_questions" : [],
        "behavioural_questions" : []
    }
    for input_question in role_question_set.question_set:
        #Check the type is valid
        if input_question.type not in valid_question_types:
            raise HTTPException(status_code=400,detail="Invalid question type encountered")
        #Get the question set according to type
        new_questions = [ *cleaned_questions.get(f"{input_question.type}_questions"), bleach.clean(input_question.question_text)]
        cleaned_questions[f"{input_question.type}_questions"] = new_questions
    async with SessionLocal() as session:
        #Add the questions to the role
        await Question.add_questions_from_ai_json(
            session,
            role_id=role_question_set.role_id,
            data=cleaned_questions
        )
        #Get the role to output as the response
        role_data = await JobRole.get_role_with_questions_by_id(session,role_id=role_question_set.role_id)
        role_response = RoleResponseSchema.model_validate(role_data)
    return role_response




@router.get("/getroleswithquestions", response_model = List[RoleResponseSchema])
async def get_roles_with_questions(api_key: str = Depends(get_api_key)):
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
async def start_interview(role_id: int | None = Query(None), api_key: str = Depends(get_api_key)):
    """
        Starts a session by creating an entry in the sessions table
    """

    try:
        async with SessionLocal() as session:
            session = await Session.create_session(db=session, thread_id=None, role_id=role_id)
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

    
@router.post("/scoreandsuggestanswer", response_model = ScoredAnswerSchema, status_code=status.HTTP_201_CREATED)
async def score_and_suggest_answer(role_q_a_input : RoleQuestionAnswerInputSchema, api_key: str = Depends(get_api_key)):
    """
        Scores the user's answer and suggests an alternative answer
    """
    async with SessionLocal() as session:
        question = await Question.get_by_id(session, role_q_a_input.question_id)
        #print("Question Received", question)
        print("Question Received", question.question_text, question.role.id)
        #Get the response from AI
        ai_response = get_score_and_suggested_answer(question.role.role_name,question.role.role_text,question.question_text, role_q_a_input.user_answer)
        # print("------------------------")
        # print("AI RESPONSE", ai_response)
        # print("------------------------")
        #ai_response = {'score': 1, 'suggested_answer': 'To ensure smooth implementation of a new security control across multiple environments, I would begin by fully understanding the technical architecture and relevant security requirements, as demonstrated through my prior experience with [specific technology or project from CV]. I would collaborate closely with project and architecture teams to analyse risks and define implementation requirements. Next, I would devise and document a deployment plan, including a comprehensive risk assessment and clear rollout steps. I would ensure proper configuration and integration with existing SIEM/SOAR tools and cloud environments, following secure-by-design principles. Throughout the process, I would engage stakeholders for feedback, perform controlled testing in a non-production environment, and monitor the rollout for issues. Post-implementation, I would review the controls for effectiveness, ensure documentation is up to date, and recommend continuous improvement actions based on outcomes and emerging trends.'}
        #Add the user's answer to the question and the suggested answer
        user_answer = await Answer.create_answer(session,int(role_q_a_input.session_id),question.id,role_q_a_input.user_answer)
        suggested_answer = await Answer.create_answer(session,int(role_q_a_input.session_id),question.id,ai_response["suggested_answer"])
        scored_answer = await ScoredAnswer.create_scored_answer(
            session,
            ai_response["score"],
            int(role_q_a_input.session_id),
            question.id,
            user_answer.id,
            suggested_answer.id)

        
        # session = await Session.get_session_with_questions_and_answers(session,int(role_q_a_input.session_id))

        # print("CREATED SCORED ANSWER", session.scored_answers)
        # scored_answer = session.scored_answers[0]
        #Gather data for response output
        user_answer_res = AnswerSchema.model_validate(scored_answer.user_answer)
        suggested_answer_res = AnswerSchema.model_validate(scored_answer.suggested_answer)
        question_res = QuestionSchema.model_validate(scored_answer.scored_question)

        scored_answer_response= ScoredAnswerSchema(
                scored_answer_id=scored_answer.id,
                score =scored_answer.score,
                question = question_res,
                user_answer = user_answer_res,
                suggested_answer = suggested_answer_res  
        )
    return scored_answer_response


@router.get("/getsessionscoredanswers", response_model = RoleAndSessionResponseSchema)
async def get_session_scored_answers(session_id: int = Query(), api_key: str = Depends(get_api_key)):
    """
        Get the session with scored answers
    """
    async with SessionLocal() as session:
        session = await Session.get_session_with_scored_answers(session,int(session_id))
        print("SESSION ROLE", session.job_role.questions)

        scored_answers = []
        for scored_answer in session.scored_answers:
            user_answer = AnswerSchema.model_validate(scored_answer.user_answer)
            suggested_answer = AnswerSchema.model_validate(scored_answer.suggested_answer)
            question = QuestionSchema.model_validate(scored_answer.scored_question)

            scored_answers.append(ScoredAnswerSchema(
                scored_answer_id=scored_answer.id,
                score =scored_answer.score,
                question = question,
                user_answer = user_answer,
                suggested_answer = suggested_answer
            ))
        scored_session_response = ScoredSessionResponseSchema(
            id = session.id,
            scored_answers = scored_answers
        )
        role_response = RoleResponseSchema.model_validate(session.job_role)
        # role_response = RoleResponseSchema(
        #     id=session.job_role.id,
        #     role_name=session.job_role.role_name,
        #     role_text=session.job_role.role_text,
        #     quetions=session.job_role.questions
        # )

        role_and_session_response = RoleAndSessionResponseSchema(
            role = role_response,
            scored_session=scored_session_response
        )
        print("Session with scored answers", role_and_session_response)
        return role_and_session_response



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

        return session_response

# @router.get("/getallsessions", response_model = List[SessionRoleResponseSchema])
# async def get_all_sessions():
#     async with SessionLocal() as session:
#         sessions = await Session.get_all_sessions(session)
#         session_list = []
#         for session_res in sessions:
#             session_response_obj = SessionRoleResponseSchema.model_validate(session_res)
#             session_list.append(
#                 session_response_obj
#             )
#         return session_list

@router.get("/getallsessions", response_model = PaginatedResponse)
async def get_all_sessions(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    async with SessionLocal() as session:
        sessions, total = await Session.get_all_sessions(
            session,
            page=page,
            page_size=page_size
        )

        session_list = [
            SessionRoleResponseSchema.model_validate(s)
            for s in sessions
        ]

        total_pages = ceil(total / page_size)

        # Build next page URL
        next_page: Optional[str] = None
        if len(sessions) == page_size:
            next_page = str(
                request.url.include_query_params(
                    page=page + 1,
                    page_size=page_size
                )
            )

        return {
            "data": session_list,
            "next_page": next_page,
            "total": total,
            "total_pages": total_pages,
            "page": page,
            "page_size": page_size
        }