
from openai import OpenAI
import os, dotenv,json
from pathlib import Path
from data.models import JobRole
from data.db import SessionLocal
import asyncio
import uuid

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

dotenv_file = PROJECT_ROOT / ".env"

if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)

API_KEY = os.environ.get("OPENAI_API_KEY")


def start_interview():
    client = OpenAI(api_key=API_KEY)

    thread = client.beta.threads.create()

    return thread.id

# def generate_ai_answer(thread_id: str, question: str):
#     client = OpenAI(api_key=API_KEY)

#     prompt = f"""
#         Interview Question:
#         {question}

#         You MUST use the text in the "My job interview documents" files to answer this question.
#         If relevant, reference specific experience from the CV.
#         You are answering interview questions as Christopher Briant.

#         Always:
#         - answer in first person
#         - base responses on real experience in the CV
#         - be professional and concise
#         - do not invent experience
#     """

#     client.beta.threads.messages.create(
#         thread_id=thread_id,
#         role="user",
#         content=prompt
#     )

#     run = client.beta.threads.runs.create(
#         thread_id=thread_id,
#         assistant_id=os.environ.get("ASSISTANT_ID")
#     )

#     while run.status != "completed":
#         run = client.beta.threads.runs.retrieve(
#             thread_id=thread_id,
#             run_id=run.id
#         )

#     messages = client.beta.threads.messages.list(thread_id=thread_id)

#     return messages.data[0].content[0].text.value

def generate_ai_answer(question: str):
    """
        Generate an answer from OpenAI to an interview question 
    """
    client = OpenAI(api_key=API_KEY)

    # Send the question as a user message
    response = client.responses.create(
        prompt={
            "id": os.environ.get("OPENAI_INTVW_Q_PROMPT_ID"),
            "version": "5",
            "variables": {
            "question": f"{question}"
            }
        },
        input=[
            {
                "role": "user",
                "content": [
                    {
                    "type": "input_text",
                    "text": f"""
                        Please answer this interview question using ONLY the uploaded CV.
                        {question}

                        Requirements: 
                        -Answer in first person
                        -Do not refer to yourself by name
                        -Do not say "As Christopher Briant". 
                        -Do NOT invent experience 
                        -Reference only real experience from the uploaded CV 
                        -Be professional and concise
                    """
                    }
                ]
            },
        ],
        text={
            "format": {
                "type": "text"
            }
        },
        reasoning={},
        tools=[
            {
                "type": "file_search",
                "vector_store_ids": [
                    os.environ.get("OPENAI_CV_FILE_VECTOR_ID")
                ]
            }
        ],
        max_output_tokens=2048,
        store=True,
        include=["web_search_call.action.sources"]
    )

    # Extract the text
    # The Responses API stores the assistant text in response.output
    # It can have multiple items, each with type "message" and a "content" array
    assistant_text = ""

    for item in response.output:
        # Each item can have type "message", "tool_result", etc.
        print("ITEM", item)
        if item.type == "message":
            for content_piece in item.content:
                if content_piece.type == "output_text":
                    assistant_text += content_piece.text

    return assistant_text


def get_work_history_ai_answer(thread_id: str):
    client = OpenAI(api_key=API_KEY)

    # Send the question as a user message
    response = client.responses.create(
        prompt={
            "id": os.environ.get("OPENAI_WORK_HISTORY_PROMPT_ID"),
            "version": "1"
        },
        input=[
            {
                "role": "user",
                "content": [
                    {
                    "type": "input_text",
                    "text": "        Please list Christopher Briant's work history based on the uploaded CV.\n\n        Requirements:\n        - Answer in first person as Christopher Briant\n        - Do NOT invent any work history\n        - Reference only real work history from the uploaded CV\n        - Be professional and concise"
                    }
                ]
            },
        ]

    )

    # Extract the text
    # The Responses API stores the assistant text in response.output
    # It can have multiple items, each with type "message" and a "content" array
    assistant_text = ""

    for item in response.output:
        # Each item can have type "message", "tool_result", etc.
        print("ITEM", item)
        if item.type == "message":
            for content_piece in item.content:
                if content_piece.type == "output_text":
                    assistant_text += content_piece.text

    return assistant_text

def get_score_and_suggested_answer(job_role,job_description,question,user_answer):
    client = OpenAI(api_key=API_KEY)

    try:
        response = client.responses.create(
            prompt={
                "id": os.environ.get("OPENAI_INTVW_SUGGESTED_ANSWER_PROMPT_ID"),
                "version": "1",
                "variables": {
                    "job_description": job_description,
                    "question": question,
                    "user_answer": user_answer,
                    "job_role": job_role
                }
            },

            input=[
                {
                    "role" : "user",
                    "content" : f"""
    You are an interviewer for the job role {job_role}. 

    The job description is {job_description}


    The question asked is {question}.

    Your task is to analyse the user's answer to the question against the job descrption below and rate the user's answer based on their skills and experience based on the contents of their uploaded CV on a scale of one to ten. Also, provide an suggested answer based on the contents of thier CV. Refer to the skills and experience from the CV where necessary. Do NOT invent skills and experience. 



    Follow these rules carefully:

    1. Extract the job role title from {job_role}. 
    2. Extract the user's answer from {user_answer}. 
    3. Rate the user's response on a scale of 1 to 10 based on the job description and the users uploaded CV. ONLY provide a score value within the bounds of the scale of 1 to 10.
    4. Generate a suggested answer based on the  job description below and the users uploaded CV.




    Return ONLY valid JSON in the following format:

    {{
    "score": "int",
    "suggested_answer" : "string"

    }}"""
                }
                
            ],
            text={
                "format": {
                "type": "text"
                }
            },
            reasoning={},
            tools=[
                {
                "type": "file_search",
                "vector_store_ids": [
                    os.environ.get("OPENAI_CV_FILE_VECTOR_ID")
                ]
                }
            ],
            max_output_tokens=2048,
            store=True,
            include=["web_search_call.action.sources"]
        )
        
        response_data = response.output[1].content[0].text
        # Convert string to dict
        response_dict = json.loads(response_data)

        # Output directory
        output_dir = Path(PROJECT_ROOT) / "files/answers"
        os.makedirs(output_dir, exist_ok=True)

        output_file = output_dir / f"{uuid.uuid4()}.json"

        # Now write to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(response_dict, f, indent=2)


        print(f"✅ Interview question answer saved to: {output_file}")
        return response_dict
    except Exception as e:
        print("Error encountered while trying to get suggested answer", e)

async def main():
    #thread_id = start_interview()
    # print("THREAD STARTED", thread_id, os.environ.get("ASSISTANT_ID"))

    # work_history = get_work_history_ai_answer(thread_id)
    # print("WORK HISTORY", work_history)

    # async with SessionLocal() as session:
    #     random_questions = await JobRole.get_random_questions(session,1,1)
    #     print("RANDOM QUESTIONS", random_questions)
    #     for question in random_questions:
    #         print(question.question_text)
    #         ai_answer = generate_ai_answer(question.question_text)
    #         print("AI ANSWER", ai_answer)

    #TEST SUGGESTED ANSWER
    role_name = "Bounty Hunter"
    job_description = "The successful candidate will be a bounty hunter with eleven years experience. They must be physically strong. Possessing superpowers will be an advantage. Bescar armour will be provided, but we prefer it if you have your own. The job will require travelling to other planets so own spaceship with a working hyperdrive is required."
    question = "Describe your experience with advanced weaponry and how you select the appropriate tools for a mission."
    user_answer = "I haven't had any experience with advanced weaponry, but I have fired an air rifle at a fair ground"

    response_data = get_score_and_suggested_answer(role_name,job_description,question,user_answer)
    print("HERE IS THE RESPONSE", response_data)




if __name__ == "__main__":
    asyncio.run(main())
