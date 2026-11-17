#!/usr/bin/env python3
"""
NEETFlow Entry Point: Launches the Web Application & Server.
Run directly with:
    python3 app.py
"""

import sys
import argparse
from neetflow import database, scheduler, server

def main():
    parser = argparse.ArgumentParser(description="NEETFlow: 4-Subject Dynamic Prep Engine & Test Arena")
    parser.add_argument("--port", type=int, default=8000, help="Port to run server on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    args = parser.parse_args()

    # Initialize SQLite database
    print("📦 Initializing NEETFlow SQLite database...")
    database.init_db()

    # Seed default 6-month timeline if none exists
    latest = database.get_latest_timeline()
    if not latest:
        print("🌱 Seeding default 6-Month (180-Day) NEET Preparation Roadmap...")
        timeline_id = database.save_timeline(
            name="6-Month NEET Crash Course",
            total_days=180,
            daily_hours=10.0,
            start_date=""
        )
        roadmap = scheduler.generate_roadmap(
            timeline_id=timeline_id,
            total_days=180,
            daily_hours=10.0
        )
        database.save_daily_tasks(roadmap["tasks"])
        print(f"✅ Generated {len(roadmap['tasks'])} tasks across Botany, Zoology, Physics & Chemistry!")

    print(f"\n=======================================================")
    print(f" 🩺 NEETFlow is ready! Open your browser at:")
    print(f" 👉 http://localhost:{args.port}")
    print(f"=======================================================\n")

    server.run_server(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
