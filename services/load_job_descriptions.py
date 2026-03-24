from openai import OpenAI
import os, dotenv,json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

dotenv_file = PROJECT_ROOT / ".env"

if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)

API_KEY = os.environ.get("OPENAI_API_KEY")


def load_job_description_file_names():
    files_directory = PROJECT_ROOT / "files/job_descriptions"
    job_description_files = [f for f in files_directory.glob("*.txt") if f.is_file()]
    for file_name in job_description_files:
        print(file_name)
    return job_description_files


# def get_interview_questions_from_ai(job_description_file):
#     #Get the file name without extension, use .stem to get the filename without the extension
#     file_path = Path(job_description_file)
#     file_name_without_ext = file_path.stem
#     print("FILE NAME", file_name_without_ext)
#     #Read the file
#     file_text = ""
#     with open(job_description_file, "r", encoding="utf-8") as f:
#         file_text = f.read()
#     #print("FILE CONTENT", file_text)

#     if API_KEY:
#         # --- CONFIGURATION ---
#         # You can set your API key here, or use environment variable OPENAI_API_KEY
#         client = OpenAI(api_key=API_KEY)

#         # --- PROMPT FOR AI ---
#         prompt = """
#         Generate an array of job interview questions based on the text within the job description. Each question needs to be unique.     

#         Output as a json structure with the top level being formatted as below:
#             {
#                 "role_name": "string",
#                 "questions": ["list", "of", "questions"],
#             }
#         """

#         # --- API CALL ---
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",  # You can use "gpt-4o" or "gpt-4-turbo" for larger outputs
#             messages=[
#                 {"role": "system", "content": f"You are an interviewer for the role provided in the job description."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.8,
#             max_tokens=4000  # increase if you want more output (may need pagination)
#         )

#         # --- EXTRACT TEXT OUTPUT ---
#         response_data = response.choices[0].message.content.strip()

#         # --- SAVE TO FILE ---
#         output_dir = PROJECT_ROOT / "files/job_descriptions/out"
#         output_file = os.path.join(output_dir, f"{file_name_without_ext}.json")
#         with open(output_file, "w", encoding="utf-8") as f:
#             f.write(response_data)

#         print(f"✅ Response data generated and saved to {output_file}")

def get_interview_questions_from_ai(job_description_file):

    # Get filename without extension
    file_path = Path(job_description_file)
    file_name_without_ext = file_path.stem
    print("FILE NAME:", file_name_without_ext)

    # Read job description
    with open(job_description_file, "r", encoding="utf-8") as f:
        file_text = f.read()

    if not API_KEY:
        print("❌ API key not configured.")
        return

    client = OpenAI(api_key=API_KEY)

    # --- HIGH QUALITY PROMPT ---
    prompt = """
You are a senior technical interviewer designing an interview for a candidate.

Your task is to analyse the job description and generate realistic interview questions
that a hiring panel would ask for this role.

Follow these rules carefully:

1. Extract the job role title from the job description.
2. Identify the key technologies, responsibilities, and seniority level.
3. Generate high-quality interview questions relevant to the role.

The questions must include:

• Technical deep-dive questions
• Architecture / design questions
• Scenario / troubleshooting questions
• Behavioural experience questions

The questions should resemble real interviews at strong engineering organisations.

Avoid generic questions. Focus on:
- real implementation details
- system design decisions
- troubleshooting scenarios
- security considerations
- operational experience

Return ONLY valid JSON in the following format:

{
  "role_name": "string",
  "technical_questions": [
    "question"
  ],
  "architecture_questions": [
    "question"
  ],
  "scenario_questions": [
    "question"
  ],
  "behavioural_questions": [
    "question"
  ]
}

Requirements:
- Generate 5 questions per category
- Each question must be unique
- Do not include explanations
- Do not include markdown
- Output valid JSON only
"""

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            max_tokens=2000,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You generate structured interview questions from job descriptions."
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nJOB DESCRIPTION:\n{file_text}"
                }
            ]
        )

        response_data = response.choices[0].message.content.strip()
        # Convert string to dict
        response_dict = json.loads(response_data)

        # Add role_text
        response_dict["role_text"] = file_text
        
        # Output directory
        output_dir = Path(PROJECT_ROOT) / "files/job_descriptions/out"
        os.makedirs(output_dir, exist_ok=True)

        output_file = output_dir / f"{file_name_without_ext}.json"

        # Now write to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(response_dict, f, indent=2)

  

        # Save response
        # with open(output_file, "w", encoding="utf-8") as f:
        #     f.write(response_data)

        print(f"✅ Interview questions saved to: {output_file}")

    except Exception as e:
        print("❌ Error generating interview questions:", str(e))



if __name__ == "__main__":
    job_description_files = load_job_description_file_names()
    get_interview_questions_from_ai(job_description_files[1])