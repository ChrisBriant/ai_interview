from .db import Base, AsyncSession, SessionLocal
from typing import List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    TIMESTAMP,
    DateTime,
    func,
    Enum,
    select,
    update
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

    session =  relationship(
        "Session",
        back_populates="job_role"
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
        # await Question.add_questions_from_ai_json(db, role.id, data)

        # await db.commit()

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

    @classmethod
    async def get_random_questions(
        cls,
        db: AsyncSession,
        role_id: int,
        limit: int = 5
    ):
        """
        Fetch `limit` random questions for the given role_id.
        """
        # Build the query
        stmt = (
            select(Question)
            .where(Question.role_id == role_id)
            .order_by(func.random())
            .limit(limit)
        )

        # Execute against the async session
        result = await db.execute(stmt)

        # Return list of Question objects
        questions = result.scalars().all()
        return questions


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

    answers = relationship(
        "Answer",
        back_populates = "question",
        cascade="all, delete-orphan"
    )

    scored_answers = relationship(
        "ScoredAnswer",
        back_populates="scored_question",
        cascade="all, delete-orphan"
    )

    @classmethod
    async def get_by_id(cls, db: AsyncSession, question_id: int) -> List["Question"]:
        """
            Fetch a single question.
        """
        stmt = select(cls).options(
            selectinload(cls.role),
        ).where(
            cls.id == question_id
        )
        result = await db.execute(stmt)
        question = result.scalar_one()
        return question

    @classmethod
    async def get_by_ids(cls, db: AsyncSession, question_ids: List[int]) -> List["Question"]:
        """
        Fetch questions given a list of question IDs.
        """
        stmt = select(cls).where(cls.id.in_(question_ids))
        result = await db.execute(stmt)
        questions = result.scalars().all()
        return questions

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

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    thread_id = Column(
        String,
        nullable=True
    )
    #Optional role ID if the interview session is linked to one job role
    role_id = Column(
        Integer,
        ForeignKey("jobroles.id", ondelete="CASCADE"),
        nullable=True
    )
    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    finished_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
 
    question_answers = relationship(
        "Answer",
        back_populates="session"
    )

    scored_answers = relationship(
        "ScoredAnswer",
        back_populates="session"
    )

    job_role = relationship(
        "JobRole",
        back_populates="session"
    )
    
    @classmethod
    async def exists(cls, db: AsyncSession, session_id: int) -> bool:
        """
        Check if a session with the given ID exists in the database.
        Returns True if it exists, False otherwise.
        """
        result = await db.execute(
            select(cls.id).where(cls.id == session_id)
        )
        return result.scalar() is not None

    @classmethod
    async def create_session(cls, db: AsyncSession, thread_id: str | None, role_id : int | None):
        session = cls(thread_id=thread_id, role_id=role_id)

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session

    @classmethod
    async def close_session(cls, db: AsyncSession, session_id: int):

        stmt = (
            update(cls)
            .where(cls.id == session_id)
            .values(finished_at=datetime.now(timezone.utc))
        )

        await db.execute(stmt)
        await db.commit()

    @classmethod
    async def get_thread_id(cls, db: AsyncSession, session_id: int):

        result = await db.execute(
            select(cls.thread_id).where(cls.id == session_id)
        )

        return result.scalar_one_or_none()

    @classmethod
    async def get_session_with_questions_and_answers(cls, db: AsyncSession, session_id: int):
        """
        Fetch a session by ID, including all questions and their associated answers.
        """
        result = await db.execute(
            select(cls)
            .where(cls.id == session_id)
            .options(
                selectinload(cls.question_answers)
                .selectinload(Answer.question)  # load linked question for each answer
            )
        )

        session_obj = result.scalar_one_or_none()
        return session_obj

    @classmethod
    async def get_session_with_scored_answers(cls, db: AsyncSession, session_id: int):
        """
        Fetch a session by ID, including all questions and their associated answers.
        """
        sa_loader = selectinload(cls.scored_answers)

        result = await db.execute(
            select(cls)
            .where(cls.id == session_id)
            .options(
                selectinload(cls.job_role).selectinload(JobRole.questions),
                sa_loader.selectinload(ScoredAnswer.scored_question),
                sa_loader.selectinload(ScoredAnswer.user_answer),
                sa_loader.selectinload(ScoredAnswer.suggested_answer),
            )
        )

        session_obj = result.scalar_one_or_none()
        return session_obj

    @classmethod
    async def get_all_sessions(cls, db: AsyncSession):
        result = await db.execute(
            select(cls)
            .options(
                selectinload(cls.job_role)
            )
        )

        return result.scalars().all()
    

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True)
    answer_text = Column(Text, nullable=False)
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False
    )
    added_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    question = relationship(
        "Question",
        back_populates="answers"
    )

    session = relationship(
        "Session",
        back_populates="question_answers"
    ) 


    # Scored as user's answer
    scored_as_user = relationship(
        "ScoredAnswer",
        foreign_keys="ScoredAnswer.user_answer_id",
        back_populates="user_answer",
        cascade="all, delete-orphan"
    )

    # Scored as suggested answer
    scored_as_suggested = relationship(
        "ScoredAnswer",
        foreign_keys="ScoredAnswer.suggested_answer_id",
        back_populates="suggested_answer",
        cascade="all, delete-orphan"
    )

    @classmethod
    async def create_answer(
        cls,
        db: AsyncSession,
        session_id: int,
        question_id: int,
        answer_text: str
    ):
        answer = cls(
            session_id=session_id,
            question_id=question_id,
            answer_text=answer_text
        )

        db.add(answer)
        await db.commit()
        await db.refresh(answer)

        return answer

    @classmethod
    async def create_answers_bulk(cls, db: AsyncSession, session_id: int, answers: list[dict]):
        """
        Bulk create answers and return the session object with all questions and answers loaded.
        `answers` is a list of dicts:
        [
            {"question_id": 1, "answer_text": "..."},
            {"question_id": 2, "answer_text": "..."},
        ]
        """
        # Create Answer objects
        objects = [
            cls(
                session_id=session_id,
                question_id=a["question_id"],
                answer_text=a["answer_text"]
            )
            for a in answers
        ]

        # Add and commit
        db.add_all(objects)
        await db.commit()

        # Load the session with all questions and answers
        result = await db.execute(
            select(Session)
            .where(Session.id == session_id)
            .options(
                selectinload(Session.question_answers)
                .selectinload(Answer.question)  # optional: eager load question data too
            )
        )

        session_obj = result.scalar_one_or_none()
        return session_obj

class ScoredAnswer(Base):
    #Needs a model that stores the score, question_id, user_answer_id, suggested_answer_id
    __tablename__ = "scored_answers"

    id = Column(Integer, primary_key=True)
    score = Column(Integer, nullable=False)
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False
    )
    user_answer_id = Column(
        Integer,
        ForeignKey("answers.id", ondelete="CASCADE"),
        nullable=False
    )
    suggested_answer_id = Column(
        Integer,
        ForeignKey("answers.id", ondelete="CASCADE"),
        nullable=False
    )
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    added_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # ✅ Question relationship
    scored_question = relationship(
        "Question",
        back_populates="scored_answers"
    )

    # ✅ Disambiguate foreign keys
    user_answer = relationship(
        "Answer",
        foreign_keys=[user_answer_id],
        back_populates="scored_as_user"
    )

    suggested_answer = relationship(
        "Answer",
        foreign_keys=[suggested_answer_id],
        back_populates="scored_as_suggested"
    )

    session = relationship(
        "Session",
        back_populates="scored_answers"
    ) 


    @classmethod
    async def create_scored_answer(
        cls,
        db: AsyncSession,
        score: int,
        session_id : int,
        question_id: int,
        user_answer_id: str,
        suggested_answer_id: str
    ):
        scored_answer = cls(
            score=score,
            session_id=session_id,
            question_id=question_id,
            user_answer_id=user_answer_id,
            suggested_answer_id=suggested_answer_id
        )

        db.add(scored_answer)
        await db.commit()
        await db.refresh(scored_answer)

        return scored_answer

#TESTING
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



