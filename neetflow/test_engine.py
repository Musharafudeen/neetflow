from typing import List, Dict, Any
from . import database

def grade_submission(
    test_type: str,
    subject: str,
    submissions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Grades answers according to official NEET scoring scheme:
    - Correct: +4
    - Incorrect: -1
    - Unattempted: 0
    Logs incorrect attempts to Mistake Notebook.
    """
    all_questions = {q["id"]: q for q in database.get_all_questions()}

    correct_count = 0
    incorrect_count = 0
    unattempted_count = 0
    total_score = 0
    graded_details = []

    subject_breakdown: Dict[str, Dict[str, int]] = {
        "Botany": {"correct": 0, "incorrect": 0, "unattempted": 0, "score": 0},
        "Zoology": {"correct": 0, "incorrect": 0, "unattempted": 0, "score": 0},
        "Physics": {"correct": 0, "incorrect": 0, "unattempted": 0, "score": 0},
        "Chemistry": {"correct": 0, "incorrect": 0, "unattempted": 0, "score": 0}
    }

    for sub in submissions:
        qid = sub.get("question_id")
        user_answer = (sub.get("user_answer") or "").strip()
        q_obj = all_questions.get(qid)

        if not q_obj:
            continue

        q_subject = q_obj["subject"]
        if q_subject not in subject_breakdown:
            subject_breakdown[q_subject] = {"correct": 0, "incorrect": 0, "unattempted": 0, "score": 0}

        expected = q_obj["correct_answer"].strip()
        is_unattempted = not user_answer
        is_correct = False

        if is_unattempted:
            unattempted_count += 1
            delta = 0
            subject_breakdown[q_subject]["unattempted"] += 1
        else:
            # Check match (case-insensitive for write-in answers)
            if user_answer.lower() == expected.lower():
                is_correct = True
                correct_count += 1
                delta = 4
                subject_breakdown[q_subject]["correct"] += 1
            else:
                incorrect_count += 1
                delta = -1
                subject_breakdown[q_subject]["incorrect"] += 1
                # Auto-log into Mistake Notebook
                database.log_mistake(
                    question_id=qid,
                    user_answer=user_answer,
                    correct_answer=expected,
                    notes=f"Test attempt: {test_type} ({subject})"
                )

        total_score += delta
        subject_breakdown[q_subject]["score"] += delta

        graded_details.append({
            "question_id": qid,
            "question": q_obj["question"],
            "subject": q_subject,
            "chapter": q_obj["chapter"],
            "user_answer": user_answer,
            "correct_answer": expected,
            "is_correct": is_correct,
            "is_unattempted": is_unattempted,
            "score_delta": delta,
            "explanation": q_obj.get("explanation", "")
        })

    total_questions = len(submissions)
    max_possible_score = total_questions * 4
    percentage = round((total_score / max_possible_score * 100), 2) if max_possible_score > 0 else 0.0

    # Save to test results history
    result_id = database.save_test_result(
        test_type=test_type,
        subject=subject,
        total_q=total_questions,
        correct=correct_count,
        incorrect=incorrect_count,
        unattempted=unattempted_count,
        score=total_score,
        max_score=max_possible_score,
        percentage=percentage
    )

    return {
        "result_id": result_id,
        "test_type": test_type,
        "subject": subject,
        "total_questions": total_questions,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "unattempted_count": unattempted_count,
        "score": total_score,
        "max_score": max_possible_score,
        "percentage": percentage,
        "subject_breakdown": subject_breakdown,
        "details": graded_details
    }
