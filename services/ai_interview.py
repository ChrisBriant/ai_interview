
from openai import OpenAI
import os, dotenv,json
from pathlib import Path
from data.models import JobRole
from data.db import SessionLocal
import asyncio

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


async def main():
    thread_id = start_interview()
    # print("THREAD STARTED", thread_id, os.environ.get("ASSISTANT_ID"))

    # work_history = get_work_history_ai_answer(thread_id)
    # print("WORK HISTORY", work_history)

    async with SessionLocal() as session:
        random_questions = await JobRole.get_random_questions(session,1,1)
        print("RANDOM QUESTIONS", random_questions)
        for question in random_questions:
            print(question.question_text)
            ai_answer = generate_ai_answer(question.question_text)
            print("AI ANSWER", ai_answer)



if __name__ == "__main__":
    asyncio.run(main())
