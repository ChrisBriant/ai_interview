from data.models import Session
from data.schemas import QuestionAnswersSchema,AnswerSchema,SessionResponseSchema
from typing import List
from collections import defaultdict

# def construct_session_response(interview_session : Session ):
#     question_answers_list: List[QuestionAnswersSchema] = []
#     for answer in interview_session.question_answers:
#         question_answers_list.append(
#             QuestionAnswersSchema(
#                 question=answer.question,  # relies on QuestionSchema.from_attributes=True
#                 answers=[
#                     AnswerSchema(
#                         id=answer.id,
#                         answer_text=answer.answer_text,
#                         added_at=answer.added_at
#                     )
#                 ]
#             )
#         )

#     return SessionResponseSchema(
#         id=interview_session.id,
#         question_answers=question_answers_list
#     )


def construct_session_response(interview_session: Session) -> SessionResponseSchema:
    # Group answers by question id
    grouped_answers = defaultdict(list)
    for answer in interview_session.question_answers:
        grouped_answers[answer.question.id].append(answer)

    question_answers_list: List[QuestionAnswersSchema] = []

    for question_id, answers in grouped_answers.items():
        # All answers for this question
        question_answers_list.append(
            QuestionAnswersSchema(
                question=answers[0].question,  # all answers have the same question
                answers=[
                    AnswerSchema(
                        id=a.id,
                        answer_text=a.answer_text,
                        added_at=a.added_at
                    )
                    for a in answers
                ]
            )
        )

    return SessionResponseSchema(
        id=interview_session.id,
        question_answers=question_answers_list
    )