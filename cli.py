#!/usr/bin/env python3
"""
NEETFlow CLI: Command-Line Interface for Terminal Power Users.
Usage:
    python3 cli.py tasks [--day 1]
    python3 cli.py guide [--hours 10]
    python3 cli.py quiz [--subject Physics]
    python3 cli.py mistakes
    python3 cli.py new --days 180 --hours 10
"""

import sys
import argparse
from neetflow import database, scheduler, test_engine

def print_banner():
    print("""
======================================================
  🩺 NEETFlow CLI — 4-Subject Dynamic Prep Engine
  Botany • Zoology • Physics • Chemistry
======================================================
""")

def cmd_tasks(args):
    database.init_db()
    timeline = database.get_latest_timeline()
    if not timeline:
        print("❌ No timeline found. Run: python3 cli.py new --days 180 --hours 10")
        return

    day = args.day or 1
    tasks = database.get_tasks_for_day(timeline["id"], day)
    print(f"\n📋 Tasks for Day {day} of {timeline['total_days']} ({timeline['name']}):")
    print("-" * 65)
    if not tasks:
        print("  No tasks scheduled. (Buffer / Revision Day)")
        return

    for t in tasks:
        status_sym = "✅" if t["status"] == "COMPLETED" else "⏳"
        weight_tag = f"🔥 [{t.get('weightage', 'Medium')} Weightage • ~{t.get('avg_questions', 2)} Qs/yr]" if t.get('weightage') == 'High' else f"[{t.get('weightage', 'Medium')} Weightage]"
        print(f" {status_sym} [{t['subject'].upper()}] {t['chapter_name']}")
        print(f"     Priority: {weight_tag} | Target: {t['allocated_hours']} hrs | Status: {t['status']}")
    print("-" * 65)

def cmd_guide(args):
    hours = args.hours or 10.0
    guide = scheduler.calculate_daily_hour_guidelines(hours)
    print(f"\n⏱️ Recommended Daily Study Breakdown for {hours} Hours/Day:")
    print("-" * 65)
    print(f"  🌿 Botany (180 Marks):      {guide['botany_hours']} hours/day")
    print(f"  🧬 Zoology (180 Marks):     {guide['zoology_hours']} hours/day")
    print(f"     => Biology Combined:     {guide['biology_total_hours']} hours/day (50% NEET marks)")
    print(f"  ⚡ Physics (180 Marks):     {guide['physics_hours']} hours/day")
    print(f"  🧪 Chemistry (180 Marks):   {guide['chemistry_hours']} hours/day")
    print(f"  🔁 Spaced Revision & Test:  {guide['revision_hours']} hours/day")
    print("-" * 65)
    print(f"  📊 Weekly Study Target:     {guide['weekly_hours']} hours/week\n")

def cmd_quiz(args):
    database.init_db()
    subject = args.subject or "All"
    questions = database.get_all_questions(None if subject == "All" else subject)

    if not questions:
        print(f"No questions found for subject: {subject}")
        return

    print(f"\n📝 Starting Terminal NEET Quiz ({len(questions)} questions) — Subject: {subject}")
    print("Marking Scheme: +4 for Correct, -1 for Incorrect, 0 for Skip (Enter blank)\n")

    submissions = []
    for i, q in enumerate(questions, 1):
        print(f"Q{i} [{q['subject']} • {q['chapter']}]: {q['question']}")
        if q["type"] == "MCQ" and q["options"]:
            for opt_idx, opt in enumerate(q["options"], 1):
                print(f"   {opt_idx}. {opt}")
            user_input = input("   Your Choice (or exact text): ").strip()
            # If user typed option number 1, 2, 3...
            if user_input.isdigit() and 1 <= int(user_input) <= len(q["options"]):
                user_input = q["options"][int(user_input) - 1]
        else:
            user_input = input("   Your Answer: ").strip()

        submissions.append({"question_id": q["id"], "user_answer": user_input})
        print()

    result = test_engine.grade_submission("CLI_TEST", subject, submissions)
    print("=" * 65)
    print(f"🏆 Quiz Results:")
    print(f"  Score:        {result['score']} / {result['max_score']}")
    print(f"  Accuracy:     {result['percentage']}%")
    print(f"  Correct:      {result['correct_count']} (+4 each)")
    print(f"  Incorrect:    {result['incorrect_count']} (-1 each)")
    print(f"  Unattempted:  {result['unattempted_count']}")
    print("=" * 65)

    if result["incorrect_count"] > 0:
        print("💡 Incorrect answers have been automatically logged to your Mistake Notebook!")

def cmd_mistakes(args):
    database.init_db()
    mistakes = database.get_mistakes(only_unresolved=True)
    print(f"\n📓 Mistake Notebook ({len(mistakes)} unresolved):")
    print("-" * 65)
    if not mistakes:
        print("  🎉 No unresolved mistakes! Excellent work.")
        return

    for m in mistakes:
        print(f" ❌ [{m['subject']} - {m['chapter']}]")
        print(f"    Q: {m['question']}")
        print(f"    Your Wrong Answer: {m['user_answer']}")
        print(f"    Correct NCERT Answer: {m['correct_answer']}")
        if m["explanation"]:
            print(f"    Insight: {m['explanation']}")
        print()
    print("-" * 65)

def cmd_new(args):
    database.init_db()
    days = args.days or 180
    hours = args.hours or 10.0
    name = f"{days}-Day NEET Preparation Plan"

    timeline_id = database.save_timeline(name, days, hours, "")
    roadmap = scheduler.generate_roadmap(timeline_id, days, hours)
    database.save_daily_tasks(roadmap["tasks"])

    print(f"\n🎉 Successfully created new timeline: '{name}'!")
    print(f"  Total Days: {days} ({roadmap['syllabus_coverage_days']} syllabus + {roadmap['grand_mock_phase_days']} grand mocks)")
    print(f"  Tasks Scheduled: {len(roadmap['tasks'])}")
    print(f"  Daily Study Capacity: {hours} hrs/day")
    print(f"  Run `python3 cli.py tasks --day 1` or `python3 app.py` to view it.\n")

def main():
    print_banner()
    parser = argparse.ArgumentParser(description="NEETFlow CLI")
    subparsers = parser.add_subparsers(dest="command")

    # tasks
    p_tasks = subparsers.add_parser("tasks", help="List tasks for a specific day")
    p_tasks.add_argument("--day", type=int, default=1, help="Day number (e.g. 1)")

    # guide
    p_guide = subparsers.add_parser("guide", help="Show hour guidelines by subject")
    p_guide.add_argument("--hours", type=float, default=10.0, help="Total daily study hours")

    # quiz
    p_quiz = subparsers.add_parser("quiz", help="Take an interactive test")
    p_quiz.add_argument("--subject", type=str, default="All", choices=["All", "Botany", "Zoology", "Physics", "Chemistry"])

    # mistakes
    subparsers.add_parser("mistakes", help="View unresolved mistake log")

    # new
    p_new = subparsers.add_parser("new", help="Create a custom n-day timeline roadmap")
    p_new.add_argument("--days", type=int, default=180, help="Customizable timeline length in n days (e.g. 45, 60, 75, 90, 120, 180, 240, 365)")
    p_new.add_argument("--hours", type=float, default=10.0, help="Hours per day (e.g. 10.0)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "tasks":
        cmd_tasks(args)
    elif args.command == "guide":
        cmd_guide(args)
    elif args.command == "quiz":
        cmd_quiz(args)
    elif args.command == "mistakes":
        cmd_mistakes(args)
    elif args.command == "new":
        cmd_new(args)

if __name__ == "__main__":
    main()
