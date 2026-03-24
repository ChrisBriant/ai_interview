from .db import Base, AsyncSession, SessionLocal
from typing import List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    TIMESTAMP,
    func,
    Enum,
    select
)
from sqlalchemy.orm import relationship, selectinload
from .schemas import RoleResponseSchema, QuestionSchema
import enum
import os, dotenv
from pathlib import Path
import json
import asyncio


class QuestionType(enum.Enum):
    technical = "technical"
    architecture = "architecture"
    scenario = "scenario"
    behavioural = "behavioural"


class JobRole(Base):
    __tablename__ = "jobroles"

    id = Column(Integer, primary_key=True, index=True)

    role_name = Column(String, nullable=False)
    role_text = Column(Text, nullable=False, unique=True)

    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        nullable=False
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

    questions = relationship(
        "Question",
        back_populates="role",
        cascade="all, delete-orphan"
    )


    @classmethod
    async def create_from_ai_json(
        cls,
        db: AsyncSession,
        data: dict
    ):
        role = cls(
            role_name=data["role_name"],
            role_text=data["role_text"]
        )

        db.add(role)

        await db.flush()  # ensures role.id exists

        await Question.add_questions_from_ai_json(
            db,
            role.id,
            data
        )

        await db.commit()

        #await db.refresh(role)


        await db.flush()  # ensures role.id exists

        # Add questions
        await Question.add_questions_from_ai_json(db, role.id, data)

        await db.commit()

        # Eagerly load questions before returning
        result = await db.execute(
            select(cls).options(selectinload(cls.questions)).where(cls.id == role.id)
        )
        role_with_questions = result.scalar_one()

        return role_with_questions

    @classmethod
    async def get_all_roles(cls, db: AsyncSession) -> List["JobRole"]:
        """
        Fetch all job roles from the database.
        Returns a list of JobRole objects.
        """
        result = await db.execute(select(cls))

        result = await db.execute(
            select(cls).options(selectinload(cls.questions))  # eager load questions
        )
        roles = result.scalars().all()
        return roles

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)

    role_id = Column(
        Integer,
        ForeignKey("jobroles.id", ondelete="CASCADE"),
        nullable=False
    )

    question_type = Column(
        Enum(QuestionType),
        nullable=False
    )

    question_text = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        nullable=False
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

    role = relationship(
        "JobRole",
        back_populates="questions"
    )

    @classmethod
    async def add_questions_from_ai_json(
        cls,
        db: AsyncSession,
        role_id: int,
        data: dict
    ):
        question_map = {
            "technical_questions": "technical",
            "architecture_questions": "architecture",
            "scenario_questions": "scenario",
            "behavioural_questions": "behavioural",
        }

        for json_key, qtype in question_map.items():

            questions = data.get(json_key, [])

            for q in questions:

                question = cls(
                    role_id=role_id,
                    question_type=qtype,
                    question_text=q
                )

                db.add(question)



async def load_job_questions_from_json(json_data):
    try:
        async with SessionLocal() as session:
            role = await JobRole.create_from_ai_json(
                db=session,
                data=json_data
            )

            questions_list = [QuestionSchema(
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

            print("ROLE DATA COMPLETED", role_data)
            return role_data
    except Exception as e:
        print("FAILED TO UPDATE DATABASE", e)

async def fetch_job_roles():
    try:
        async with SessionLocal() as session:
            roles = await JobRole.get_all_roles(db=session)
            print("HERE ARE ALL THE ROLES", roles)
    except Exception as e:
        print("ERROR GETTING THE ROLES",e)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

dotenv_file = PROJECT_ROOT / ".env"
files_dir = PROJECT_ROOT / "files"

if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)

if __name__ == "__main__":
    files_directory = PROJECT_ROOT / "files/job_descriptions/out"
    processed_directory = PROJECT_ROOT / "files/job_descriptions/processed"
    processed_directory.mkdir(parents=True, exist_ok=True)

    job_role_json_files = [f for f in files_directory.glob("*.json") if f.is_file()]
    for job_role_file in job_role_json_files:
        try:
            with open(job_role_file, 'r') as file:
                role_data_dict = json.load(file)
                print(role_data_dict)
                file.close()
                #Put the data into the database
                asyncio.run(load_job_questions_from_json(role_data_dict))
                # Move file after successful processing
                destination = processed_directory / job_role_file.name
                print("DESTINATION", destination)
                job_role_file.rename(destination)
        except Exception as e:
            print(e)

    #Get the job roles from the database
    #asyncio.run(fetch_job_roles())



