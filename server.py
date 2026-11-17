import json
import mimetypes
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from . import database
from . import scheduler
from . import test_engine

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

class NEETFlowRequestHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status_code=200):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # API Routes
        if path == "/api/guidelines":
            hours = float(params.get("hours", [10.0])[0])
            guidelines = scheduler.calculate_daily_hour_guidelines(hours)
            self.send_json(guidelines)
            return

        elif path == "/api/chapters":
            chapters = scheduler.load_chapters()
            self.send_json(chapters)
            return

        elif path == "/api/timeline":
            timeline = database.get_latest_timeline()
            if timeline:
                stats = database.get_timeline_stats(timeline["id"])
                hour_guide = scheduler.calculate_daily_hour_guidelines(timeline["daily_hours"])
                self.send_json({"timeline": timeline, "stats": stats, "hour_guide": hour_guide})
            else:
                self.send_json({"timeline": None})
            return

        elif path == "/api/tasks":
            timeline_id = int(params.get("timeline_id", [1])[0])
            day_number = int(params.get("day", [1])[0])
            tasks = database.get_tasks_for_day(timeline_id, day_number)
            self.send_json(tasks)
            return

        elif path == "/api/questions":
            subject = params.get("subject", [None])[0]
            questions = database.get_all_questions(subject)
            # Remove correct answer from questions sent for tests if requested, but for now we supply the question set
            self.send_json(questions)
            return

        elif path == "/api/mistakes":
            only_unresolved = params.get("unresolved", ["true"])[0].lower() == "true"
            mistakes = database.get_mistakes(only_unresolved)
            self.send_json(mistakes)
            return

        elif path == "/api/study_log":
            logs = database.get_study_logs()
            self.send_json(logs)
            return

        # Serve static files (HTML, CSS, JS)
        if path == "/" or path == "":
            filepath = os.path.join(STATIC_DIR, "index.html")
        else:
            filepath = os.path.join(STATIC_DIR, path.lstrip("/"))

        if os.path.exists(filepath) and not os.path.isdir(filepath):
            mime_type, _ = mimetypes.guess_type(filepath)
            mime_type = mime_type or "application/octet-stream"
            try:
                with open(filepath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if path == "/api/timeline":
            name = payload.get("name", "NEET Mission Plan")
            total_days = int(payload.get("total_days", 180))
            daily_hours = float(payload.get("daily_hours", 10.0))
            start_date = payload.get("start_date")

            timeline_id = database.save_timeline(name, total_days, daily_hours, start_date or "")
            roadmap = scheduler.generate_roadmap(timeline_id, total_days, daily_hours, start_date)
            database.save_daily_tasks(roadmap["tasks"])

            self.send_json({
                "message": "Timeline created successfully",
                "timeline_id": timeline_id,
                "summary": {
                    "total_days": roadmap["total_days"],
                    "syllabus_coverage_days": roadmap["syllabus_coverage_days"],
                    "grand_mock_phase_days": roadmap["grand_mock_phase_days"],
                    "hour_guidelines": roadmap["hour_guidelines"],
                    "total_tasks_scheduled": roadmap["total_tasks_scheduled"]
                }
            })
            return

        elif path == "/api/tasks/toggle":
            task_id = int(payload.get("task_id", 0))
            status = payload.get("status", "COMPLETED")
            database.update_task_status(task_id, status)
            self.send_json({"success": True, "task_id": task_id, "status": status})
            return

        elif path == "/api/test/grade":
            test_type = payload.get("test_type", "PRACTICE_TEST")
            subject = payload.get("subject", "All")
            submissions = payload.get("submissions", [])
            result = test_engine.grade_submission(test_type, subject, submissions)
            self.send_json(result)
            return

        elif path == "/api/mistakes/resolve":
            mistake_id = int(payload.get("mistake_id", 0))
            database.resolve_mistake(mistake_id)
            self.send_json({"success": True, "mistake_id": mistake_id})
            return

        elif path == "/api/study_log":
            log_date = payload.get("log_date")
            botany = float(payload.get("botany_hours", 0.0))
            zoology = float(payload.get("zoology_hours", 0.0))
            physics = float(payload.get("physics_hours", 0.0))
            chemistry = float(payload.get("chemistry_hours", 0.0))
            revision = float(payload.get("revision_hours", 0.0))
            notes = payload.get("notes", "")

            database.log_daily_study(log_date, botany, zoology, physics, chemistry, revision, notes)
            self.send_json({"success": True})
            return

        self.send_response(404)
        self.end_headers()

def run_server(host="0.0.0.0", port=8000):
    database.init_db()
    server_address = (host, port)
    httpd = HTTPServer(server_address, NEETFlowRequestHandler)
    print(f"🚀 NEETFlow is running at http://localhost:{port}")
    print(f"📂 Serving static files from {STATIC_DIR}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping NEETFlow server...")
        httpd.server_close()
