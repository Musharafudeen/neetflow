import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "neetflow.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS timelines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        total_days INTEGER NOT NULL,
        daily_hours REAL NOT NULL,
        start_date TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS daily_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timeline_id INTEGER NOT NULL,
        day_number INTEGER NOT NULL,
        scheduled_date TEXT NOT NULL,
        subject TEXT NOT NULL,
        chapter_id TEXT NOT NULL,
        chapter_name TEXT NOT NULL,
        task_type TEXT NOT NULL, -- PRIMARY_STUDY, REVISION, MOCK_TEST
        allocated_hours REAL NOT NULL,
        status TEXT DEFAULT 'PENDING', -- PENDING, COMPLETED
        completed_at TIMESTAMP,
        weightage TEXT DEFAULT 'Medium',
        avg_questions INTEGER DEFAULT 2,
        FOREIGN KEY (timeline_id) REFERENCES timelines (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS questions (
        id TEXT PRIMARY KEY,
        subject TEXT NOT NULL,
        chapter TEXT NOT NULL,
        type TEXT NOT NULL, -- MCQ, WRITE_ANSWER
        question TEXT NOT NULL,
        options TEXT, -- JSON array of strings
        correct_answer TEXT NOT NULL,
        explanation TEXT
    );

    CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_type TEXT NOT NULL,
        subject TEXT NOT NULL,
        total_questions INTEGER NOT NULL,
        correct_count INTEGER NOT NULL,
        incorrect_count INTEGER NOT NULL,
        unattempted_count INTEGER NOT NULL,
        score INTEGER NOT NULL,
        max_score INTEGER NOT NULL,
        percentage REAL NOT NULL,
        taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS mistake_notebook (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id TEXT NOT NULL,
        user_answer TEXT,
        correct_answer TEXT NOT NULL,
        notes TEXT,
        resolved INTEGER DEFAULT 0,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (question_id) REFERENCES questions (id)
    );

    CREATE TABLE IF NOT EXISTS study_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT UNIQUE NOT NULL,
        botany_hours REAL DEFAULT 0,
        zoology_hours REAL DEFAULT 0,
        physics_hours REAL DEFAULT 0,
        chemistry_hours REAL DEFAULT 0,
        revision_hours REAL DEFAULT 0,
        notes TEXT
    );
    """)

    # Migrations for existing databases
    try:
        cursor.execute("ALTER TABLE daily_tasks ADD COLUMN weightage TEXT DEFAULT 'Medium'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE daily_tasks ADD COLUMN avg_questions INTEGER DEFAULT 2")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    seed_questions_if_needed()

def seed_questions_if_needed():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM questions")
    count = cursor.fetchone()["count"]

    if count == 0:
        questions_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "questions.json")
        if os.path.exists(questions_file):
            with open(questions_file, "r") as f:
                questions = json.load(f)
                for q in questions:
                    cursor.execute("""
                        INSERT OR REPLACE INTO questions (id, subject, chapter, type, question, options, correct_answer, explanation)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        q["id"],
                        q["subject"],
                        q["chapter"],
                        q["type"],
                        q["question"],
                        json.dumps(q.get("options", [])),
                        q["correct_answer"],
                        q.get("explanation", "")
                    ))
            conn.commit()
    conn.close()

def save_timeline(name: str, total_days: int, daily_hours: float, start_date: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO timelines (name, total_days, daily_hours, start_date)
        VALUES (?, ?, ?, ?)
    """, (name, total_days, daily_hours, start_date))
    timeline_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return timeline_id

def save_daily_tasks(tasks: List[Dict[str, Any]]):
    conn = get_connection()
    cursor = conn.cursor()
    # Normalize tasks to ensure weightage and avg_questions are populated
    normalized_tasks = []
    for t in tasks:
        t_copy = dict(t)
        t_copy.setdefault("weightage", "Medium")
        t_copy.setdefault("avg_questions", 2)
        normalized_tasks.append(t_copy)

    cursor.executemany("""
        INSERT INTO daily_tasks (timeline_id, day_number, scheduled_date, subject, chapter_id, chapter_name, task_type, allocated_hours, status, weightage, avg_questions)
        VALUES (:timeline_id, :day_number, :scheduled_date, :subject, :chapter_id, :chapter_name, :task_type, :allocated_hours, :status, :weightage, :avg_questions)
    """, normalized_tasks)
    conn.commit()
    conn.close()

def get_latest_timeline() -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM timelines ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_tasks_for_day(timeline_id: int, day_number: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM daily_tasks
        WHERE timeline_id = ? AND day_number = ?
        ORDER BY task_type DESC, subject ASC
    """, (timeline_id, day_number))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_task_status(task_id: int, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    completed_at = "CURRENT_TIMESTAMP" if status == "COMPLETED" else "NULL"
    cursor.execute(f"""
        UPDATE daily_tasks
        SET status = ?, completed_at = {completed_at}
        WHERE id = ?
    """, (status, task_id))
    conn.commit()
    conn.close()

def get_timeline_stats(timeline_id: int) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total_tasks,
            SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_tasks,
            SUM(allocated_hours) as total_planned_hours,
            SUM(CASE WHEN status = 'COMPLETED' THEN allocated_hours ELSE 0 END) as completed_hours
        FROM daily_tasks
        WHERE timeline_id = ?
    """, (timeline_id,))
    res = dict(cursor.fetchone())
    conn.close()
    return res

def get_all_questions(subject: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if subject and subject.lower() != "all":
        cursor.execute("SELECT * FROM questions WHERE LOWER(subject) = LOWER(?)", (subject,))
    else:
        cursor.execute("SELECT * FROM questions")
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["options"] = json.loads(d["options"]) if d["options"] else []
        result.append(d)
    return result

def save_test_result(test_type: str, subject: str, total_q: int, correct: int, incorrect: int, unattempted: int, score: int, max_score: int, percentage: float) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO test_results (test_type, subject, total_questions, correct_count, incorrect_count, unattempted_count, score, max_score, percentage)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (test_type, subject, total_q, correct, incorrect, unattempted, score, max_score, percentage))
    result_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return result_id

def log_mistake(question_id: str, user_answer: str, correct_answer: str, notes: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mistake_notebook (question_id, user_answer, correct_answer, notes)
        VALUES (?, ?, ?, ?)
    """, (question_id, user_answer, correct_answer, notes))
    conn.commit()
    conn.close()

def get_mistakes(only_unresolved: bool = True) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT m.id as mistake_id, m.question_id, m.user_answer, m.correct_answer, m.notes, m.resolved, m.logged_at,
               q.subject, q.chapter, q.question, q.explanation
        FROM mistake_notebook m
        JOIN questions q ON m.question_id = q.id
    """
    if only_unresolved:
        query += " WHERE m.resolved = 0"
    query += " ORDER BY m.id DESC"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def resolve_mistake(mistake_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE mistake_notebook SET resolved = 1 WHERE id = ?", (mistake_id,))
    conn.commit()
    conn.close()

def log_daily_study(log_date: str, botany: float, zoology: float, physics: float, chemistry: float, revision: float, notes: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO study_logs (log_date, botany_hours, zoology_hours, physics_hours, chemistry_hours, revision_hours, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(log_date) DO UPDATE SET
            botany_hours = excluded.botany_hours,
            zoology_hours = excluded.zoology_hours,
            physics_hours = excluded.physics_hours,
            chemistry_hours = excluded.chemistry_hours,
            revision_hours = excluded.revision_hours,
            notes = excluded.notes
    """, (log_date, botany, zoology, physics, chemistry, revision, notes))
    conn.commit()
    conn.close()

def get_study_logs() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM study_logs ORDER BY log_date DESC LIMIT 30")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
