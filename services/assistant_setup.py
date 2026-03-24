"""
    For setting up an AI assistant which will have my CV and allow quesitons to be asked.
"""

from openai import OpenAI
import os, dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

dotenv_file = PROJECT_ROOT / ".env"
files_dir = PROJECT_ROOT / "files"

if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)

API_KEY=os.environ.get("OPENAI_API_KEY")


client = OpenAI(api_key=API_KEY)


def setup_assistant():
    assistant = client.beta.assistants.create(
        name="CV Interview Assistant",
        instructions = """
            You are an AI assistant trained on Chris Briant's professional career information.

            Your knowledge comes from documents such as his CV and supporting career materials.

            Your responsibilities are:

            1. Answer questions about Chris's professional background, skills, and experience.
            2. Provide accurate information based only on the supplied documents.
            3. If information is not present in the documents, say that the information is not available rather than inventing details.
            4. When explaining experience or projects, summarise them clearly and professionally.
            5. When asked, generate interview-style questions based on Chris's skills, technologies, or work history.

            Guidelines:

            - Keep answers concise and professional.
            - When discussing technical topics, explain them clearly.
            - Do not fabricate experience or projects that are not present in the documents.
            - If a question is vague, ask a clarifying question.

            Interview Mode Behaviour:

            If the user asks for interview practice, you should act as an interviewer and:
            - Ask technical questions about Chris's experience.
            - Ask behavioural questions about projects and teamwork.
            - Ask follow-up questions that explore technical depth.

            Example topics you may ask about:
            - Identity and Access Management
            - OAuth and authentication systems
            - Cloud platforms
            - Software development projects
            - System architecture

            Always rely on the provided knowledge base when generating questions or answers.
        """,
        model="gpt-4.1",
        tools=[{"type": "file_search"}],
    )

    # Create vector store
    vector_store = client.vector_stores.create(
        name="My job interview documents"
    )


    file_paths = [
        files_dir / "CV_IAM_Engineer_JAN_2026.docx",
    ]

    file_streams = [open(path, "rb") for path in file_paths]

    # Upload files
    try:
        batch = client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=file_streams
        )
    finally:
        # Close the file streams
        for f in file_streams:
            f.close()

    print(batch.status)
    print(batch.file_counts)

    # Attach vector store to assistant
    client.beta.assistants.update(
        assistant_id=assistant.id,
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store.id]
            }
        }
    )

    print("Assistant created:", assistant.id)

if __name__ == "__main__":
    setup_assistant()