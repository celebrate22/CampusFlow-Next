"""Interactive Engineering Understanding Check: scoring + quiz loop (questions live in question_bank.py).

input_fn / output_fn are parameters so tests can feed scripted answers instead of typing.
"""
import os

from .question_bank import QUESTION_BANK

VALID_CHOICES = ("A", "B", "C", "D")
EXPLAIN_QUESTION_IDS = ("Q1", "Q5")  # learner must explain at least two answers
MIN_EXPLANATION_LENGTH = 10
DEFAULT_NOTES_PATH = os.path.join("data", "understanding_notes.txt")


def normalize_choice(raw):
    """'b ' -> 'B'; anything that is not A/B/C/D -> None."""
    choice = str(raw).strip().upper()
    return choice if choice in VALID_CHOICES else None


def score_answers(answers, bank=QUESTION_BANK):
    """One point per question whose SUBMITTED answer equals the correct one. answers: {id: letter}."""
    return sum(1 for q in bank if answers.get(q["id"]) == q["correct"])


def _ask_choice(question, input_fn, output_fn):
    output_fn(f"\n{question['id']}. {question['prompt']}")
    for letter, text in question["options"].items():
        output_fn(f"  {letter}) {text}")
    while True:
        choice = normalize_choice(input_fn("Your answer (A/B/C/D): "))
        if choice:
            return choice
        output_fn("[INVALID] Please type A, B, C or D.")


def _ask_explanation(input_fn, output_fn):
    while True:
        text = str(input_fn("Briefly explain why, using an example from your code: ")).strip()
        if len(text) >= MIN_EXPLANATION_LENGTH:
            return text
        output_fn(f"[INVALID] Please write at least {MIN_EXPLANATION_LENGTH} characters.")


def run_understanding_check(input_fn=input, output_fn=print, bank=QUESTION_BANK,
                            explain_ids=EXPLAIN_QUESTION_IDS):
    """Run the quiz. Returns {"score", "total", "answers", "explanations"}.

    Feedback is shown AFTER the first choice is recorded; the score uses that first choice.
    Explanations are collected for a human mentor and are NOT auto-graded.
    """
    answers, explanations = {}, {}
    for question in bank:
        choice = _ask_choice(question, input_fn, output_fn)
        answers[question["id"]] = choice  # recorded before any feedback
        if choice == question["correct"]:
            output_fn("Correct.")
        else:
            right = question["correct"]
            output_fn(f"Not quite. The expected answer is {right}) {question['options'][right]}.")
        if question["id"] in explain_ids:
            explanations[question["id"]] = _ask_explanation(input_fn, output_fn)

    score = score_answers(answers, bank)
    output_fn(f"\nFinal score: {score}/{len(bank)}")
    return {"score": score, "total": len(bank), "answers": answers, "explanations": explanations}


def save_explanations(result, learner, path=DEFAULT_NOTES_PATH):
    """Append the score and explanations to a local note file for mentor discussion."""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    lines = [f"Learner: {learner}", f"Score: {result['score']}/{result['total']}"]
    for qid, text in result["explanations"].items():
        lines.append(f"  {qid} (answered {result['answers'][qid]}): {text}")
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n\n")
    return path