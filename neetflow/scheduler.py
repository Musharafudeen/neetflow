import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

CHAPTERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chapters.json")

def load_chapters() -> List[Dict[str, Any]]:
    if not os.path.exists(CHAPTERS_FILE):
        return []
    with open(CHAPTERS_FILE, "r") as f:
        return json.load(f)

def calculate_daily_hour_guidelines(total_daily_hours: float) -> Dict[str, Any]:
    """
    Calculates the recommended daily study hours split across the 4 NEET subjects
    and dedicated revision time based on NEET 720-mark distribution.
    - Biology (Botany + Zoology): 360 marks (50% weight) -> ~35% of daily study
    - Physics: 180 marks (25% weight) -> ~25% of daily study
    - Chemistry: 180 marks (25% weight) -> ~25% of daily study
    - Revision & DPP: ~15% of daily study
    """
    revision_hours = round(total_daily_hours * 0.15, 2)
    core_study_hours = total_daily_hours - revision_hours

    botany_hours = round(core_study_hours * 0.20, 2)
    zoology_hours = round(core_study_hours * 0.20, 2)
    physics_hours = round(core_study_hours * 0.30, 2)
    chemistry_hours = round(core_study_hours * 0.30, 2)

    return {
        "total_hours": total_daily_hours,
        "botany_hours": botany_hours,
        "zoology_hours": zoology_hours,
        "biology_total_hours": round(botany_hours + zoology_hours, 2),
        "physics_hours": physics_hours,
        "chemistry_hours": chemistry_hours,
        "revision_hours": revision_hours,
        "weekly_hours": round(total_daily_hours * 7, 1)
    }

def sort_chapters_by_weightage(chapters_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sorts chapters strictly by NEET marks weightage (High to Low):
    1. Weightage level: High (3) > Medium (2) > Low (1)
    2. Average NEET questions per year: descending (e.g. 6 Qs, 5 Qs, 4 Qs...)
    3. Estimated study hours: descending (ensuring deeper foundation first)
    """
    weight_rank = {"High": 3, "Medium": 2, "Low": 1}
    return sorted(
        chapters_list,
        key=lambda c: (
            weight_rank.get(c.get("weightage", "Medium"), 1),
            c.get("avg_questions", 0),
            c.get("est_study_hours", 0)
        ),
        reverse=True
    )

def allocate_days_to_chapters(chapters: List[Dict[str, Any]], total_days: int) -> List[Dict[str, Any]]:
    """
    Distributes total available syllabus days across chapters based on their
    estimated study hours and weightage, preserving high-to-low priority.
    Supports any custom n days (e.g. 15, 45, 90, 180, 365, etc.).
    """
    if not chapters:
        return []

    total_days = max(1, total_days)

    if total_days < len(chapters):
        # Ultra-condensed timeline: map chapters into the available n days
        result = []
        for idx, c in enumerate(chapters):
            assigned_day = min(total_days, int((idx / len(chapters)) * total_days) + 1)
            result.append({
                "chapter": c,
                "allocated_days": 1,
                "start_day": assigned_day,
                "end_day": assigned_day
            })
        return result

    total_est = sum(c.get("est_study_hours", 6) for c in chapters)
    if total_est == 0:
        total_est = len(chapters) * 6

    allocations = []
    for c in chapters:
        est = c.get("est_study_hours", 6)
        days = max(1, int(round((est / total_est) * total_days)))
        allocations.append(days)

    # Adjust rounding discrepancies so sum(allocations) == total_days
    diff = total_days - sum(allocations)
    if diff != 0:
        step = 1 if diff > 0 else -1
        for i in range(abs(diff)):
            idx = i % len(allocations)
            if step < 0 and allocations[idx] <= 1:
                continue
            allocations[idx] += step

    result = []
    cur_start_day = 1
    for c, days in zip(chapters, allocations):
        end_day = cur_start_day + days - 1
        result.append({
            "chapter": c,
            "allocated_days": days,
            "start_day": cur_start_day,
            "end_day": end_day
        })
        cur_start_day = end_day + 1

    return result

def generate_roadmap(
    timeline_id: int,
    total_days: int = 180,
    daily_hours: float = 10.0,
    start_date_str: str = None
) -> Dict[str, Any]:
    """
    Generates a full day-by-day study roadmap covering all 4 subjects,
    recommending Botany & Zoology from HIGH WEIGHTAGE to LOW from Day 1,
    with built-in spaced repetition intervals (1, 3, 7, 21 days).
    """
    if not start_date_str:
        start_date = datetime.now().date()
    else:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

    chapters = load_chapters()
    if not chapters:
        return {"tasks": [], "summary": {}}

    # Group chapters by subject and sort strictly HIGH WEIGHTAGE -> LOW
    # Botany & Zoology (and Physics & Chemistry) start with highest scoring chapters
    bot_list = sort_chapters_by_weightage([c for c in chapters if c["subject"] == "Botany"])
    zoo_list = sort_chapters_by_weightage([c for c in chapters if c["subject"] == "Zoology"])
    phy_list = sort_chapters_by_weightage([c for c in chapters if c["subject"] == "Physics"])
    chm_list = sort_chapters_by_weightage([c for c in chapters if c["subject"] == "Chemistry"])

    # Allocate 75% days for first-pass syllabus, 25% for grand mock tests & final revision
    syllabus_days = max(10, int(total_days * 0.75))
    grand_mock_days = total_days - syllabus_days

    hour_guide = calculate_daily_hour_guidelines(daily_hours)

    # Allocate chapter spans across syllabus_days
    bot_allocations = allocate_days_to_chapters(bot_list, syllabus_days)
    zoo_allocations = allocate_days_to_chapters(zoo_list, syllabus_days)
    phy_allocations = allocate_days_to_chapters(phy_list, syllabus_days)
    chm_allocations = allocate_days_to_chapters(chm_list, syllabus_days)

    tasks: List[Dict[str, Any]] = []
    completed_chapters_log: List[Dict[str, Any]] = []

    # Map allocations by day for fast lookup
    def get_active_chapter(alloc_list, day_num):
        for item in alloc_list:
            if item["start_day"] <= day_num <= item["end_day"]:
                return item
        return alloc_list[-1] if alloc_list else None

    # Daily Primary Study Tasks (Syllabus Coverage Phase)
    for day in range(1, syllabus_days + 1):
        cur_date = start_date + timedelta(days=day - 1)
        cur_date_str = cur_date.strftime("%Y-%m-%d")

        # 1. Botany Task (High Weightage First)
        bot_active = get_active_chapter(bot_allocations, day)
        if bot_active:
            chap = bot_active["chapter"]
            day_in_chap = day - bot_active["start_day"] + 1
            tot_days = bot_active["allocated_days"]
            phase_desc = "NCERT Line-by-Line & Notes" if day_in_chap == 1 else ("PYQs & NCERT Review" if day_in_chap == tot_days else "Key Concepts & Mechanisms")
            tasks.append({
                "timeline_id": timeline_id,
                "day_number": day,
                "scheduled_date": cur_date_str,
                "subject": "Botany",
                "chapter_id": chap["id"],
                "chapter_name": f"{chap['name']} ({phase_desc} - Day {day_in_chap}/{tot_days})",
                "task_type": "PRIMARY_STUDY",
                "allocated_hours": hour_guide["botany_hours"],
                "status": "PENDING",
                "weightage": chap.get("weightage", "High"),
                "avg_questions": chap.get("avg_questions", 3)
            })
            if day == bot_active["end_day"]:
                completed_chapters_log.append({"day": day, "chapter": chap})

        # 2. Zoology Task (High Weightage First)
        zoo_active = get_active_chapter(zoo_allocations, day)
        if zoo_active:
            chap = zoo_active["chapter"]
            day_in_chap = day - zoo_active["start_day"] + 1
            tot_days = zoo_active["allocated_days"]
            phase_desc = "NCERT Line-by-Line & Notes" if day_in_chap == 1 else ("PYQs & NCERT Review" if day_in_chap == tot_days else "Organ Systems & Diagrams")
            tasks.append({
                "timeline_id": timeline_id,
                "day_number": day,
                "scheduled_date": cur_date_str,
                "subject": "Zoology",
                "chapter_id": chap["id"],
                "chapter_name": f"{chap['name']} ({phase_desc} - Day {day_in_chap}/{tot_days})",
                "task_type": "PRIMARY_STUDY",
                "allocated_hours": hour_guide["zoology_hours"],
                "status": "PENDING",
                "weightage": chap.get("weightage", "High"),
                "avg_questions": chap.get("avg_questions", 3)
            })
            if day == zoo_active["end_day"]:
                completed_chapters_log.append({"day": day, "chapter": chap})

        # 3. Physics Task (High Weightage First)
        phy_active = get_active_chapter(phy_allocations, day)
        if phy_active:
            chap = phy_active["chapter"]
            day_in_chap = day - phy_active["start_day"] + 1
            tot_days = phy_active["allocated_days"]
            phase_desc = "Concept Derivations" if day_in_chap == 1 else ("PYQs & Speed Drill" if day_in_chap == tot_days else "30-40 Numericals Practice")
            tasks.append({
                "timeline_id": timeline_id,
                "day_number": day,
                "scheduled_date": cur_date_str,
                "subject": "Physics",
                "chapter_id": chap["id"],
                "chapter_name": f"{chap['name']} ({phase_desc} - Day {day_in_chap}/{tot_days})",
                "task_type": "PRIMARY_STUDY",
                "allocated_hours": hour_guide["physics_hours"],
                "status": "PENDING",
                "weightage": chap.get("weightage", "High"),
                "avg_questions": chap.get("avg_questions", 3)
            })
            if day == phy_active["end_day"]:
                completed_chapters_log.append({"day": day, "chapter": chap})

        # 4. Chemistry Task (High Weightage First)
        chm_active = get_active_chapter(chm_allocations, day)
        if chm_active:
            chap = chm_active["chapter"]
            day_in_chap = day - chm_active["start_day"] + 1
            tot_days = chm_active["allocated_days"]
            phase_desc = "NCERT & Mechanism Read" if day_in_chap == 1 else ("PYQs & Reaction Drills" if day_in_chap == tot_days else "Formula Derivations & Numericals")
            tasks.append({
                "timeline_id": timeline_id,
                "day_number": day,
                "scheduled_date": cur_date_str,
                "subject": "Chemistry",
                "chapter_id": chap["id"],
                "chapter_name": f"{chap['name']} ({phase_desc} - Day {day_in_chap}/{tot_days})",
                "task_type": "PRIMARY_STUDY",
                "allocated_hours": hour_guide["chemistry_hours"],
                "status": "PENDING",
                "weightage": chap.get("weightage", "High"),
                "avg_questions": chap.get("avg_questions", 3)
            })
            if day == chm_active["end_day"]:
                completed_chapters_log.append({"day": day, "chapter": chap})

        # Sunday / every 7th day: Add Full Weekly Revision & Chapter Test
        if day % 7 == 0:
            tasks.append({
                "timeline_id": timeline_id,
                "day_number": day,
                "scheduled_date": cur_date_str,
                "subject": "All Subjects",
                "chapter_id": f"TEST-W{day//7}",
                "chapter_name": f"Weekly Mixed NEET Unit Test {day//7} (All 4 Subjects)",
                "task_type": "MOCK_TEST",
                "allocated_hours": 3.0,
                "status": "PENDING",
                "weightage": "High",
                "avg_questions": 180
            })

    # Schedule Spaced Repetition (The 1-3-7-21 Algorithm)
    revision_intervals = [1, 3, 7, 21]
    for comp in completed_chapters_log:
        finish_day = comp["day"]
        chap = comp["chapter"]
        for interval in revision_intervals:
            rev_day = finish_day + interval
            if rev_day <= total_days:
                rev_date = start_date + timedelta(days=rev_day - 1)
                tasks.append({
                    "timeline_id": timeline_id,
                    "day_number": rev_day,
                    "scheduled_date": rev_date.strftime("%Y-%m-%d"),
                    "subject": chap["subject"],
                    "chapter_id": chap["id"],
                    "chapter_name": f"Spaced Revision (+{interval}d): {chap['name']}",
                    "task_type": f"REVISION_{interval}",
                    "allocated_hours": 0.5,
                    "status": "PENDING",
                    "weightage": chap.get("weightage", "High"),
                    "avg_questions": chap.get("avg_questions", 3)
                })

    # Schedule Grand Mock Phase (last 25% of total days)
    for day in range(syllabus_days + 1, total_days + 1):
        cur_date = start_date + timedelta(days=day - 1)
        cur_date_str = cur_date.strftime("%Y-%m-%d")
        mock_num = day - syllabus_days

        tasks.append({
            "timeline_id": timeline_id,
            "day_number": day,
            "scheduled_date": cur_date_str,
            "subject": "All 4 Subjects",
            "chapter_id": f"GRAND-MOCK-{mock_num}",
            "chapter_name": f"NEET Grand Mock Test {mock_num} (3h 20m) + Mistake Notebook Analysis",
            "task_type": "MOCK_TEST",
            "allocated_hours": round(min(daily_hours, 6.0), 1),
            "status": "PENDING",
            "weightage": "High",
            "avg_questions": 180
        })

    # Sort tasks by day_number, putting PRIMARY_STUDY first, then REVISION, then MOCK_TEST
    def task_sort_key(t):
        type_priority = 0 if t["task_type"] == "PRIMARY_STUDY" else (1 if t["task_type"].startswith("REVISION") else 2)
        # Botany first, Zoology second, Physics third, Chemistry fourth
        subject_order = {"Botany": 0, "Zoology": 1, "Physics": 2, "Chemistry": 3, "All Subjects": 4, "All 4 Subjects": 4}
        return (t["day_number"], type_priority, subject_order.get(t["subject"], 5))

    tasks.sort(key=task_sort_key)

    return {
        "timeline_id": timeline_id,
        "total_days": total_days,
        "syllabus_coverage_days": syllabus_days,
        "grand_mock_phase_days": grand_mock_days,
        "hour_guidelines": hour_guide,
        "total_tasks_scheduled": len(tasks),
        "tasks": tasks
    }
