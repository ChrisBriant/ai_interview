
from openai import OpenAI
import os, dotenv,json
from pathlib import Pat

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

def generate_ai_answer(thread_id: str, question: str):
    client = OpenAI(api_key=API_KEY)

    prompt = f"""
        Interview Question:
        {question}

        You MUST use the uploaded CV in your knowledge base to answer this question.
        If relevant, reference specific experience from the CV.
        You are answering interview questions as Christopher Briant.

        Always:
        - answer in first person
        - base responses on real experience in the CV
        - be professional and concise
        - do not invent experience
    """

    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=os.environ.get("ASSISTANT_ID")
    )

    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )

    messages = client.beta.threads.messages.list(thread_id=thread_id)

    return messages.data[0].content[0].text.value


if __name__ == "__main__":
    thread_id = start_interview()
    
    print("THREAD STARTED", thread_id)