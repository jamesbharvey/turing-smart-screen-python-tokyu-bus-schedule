import argparse
import datetime
import os
import sys

from dotenv import load_dotenv

from odpt_tokyu_bus import (
    build_timetables,
    current_calendar,
    direction_label,
    upcoming_departures,
)

load_dotenv()
CONSUMER_KEY = os.environ.get("ODPT_CONSUMER_KEY")
if not CONSUMER_KEY:
    sys.exit("Error: ODPT_CONSUMER_KEY not set in environment or .env file")

STOP_NAME = "Tamagawaonshitsumura"


def print_timetable(timetable, full=False, now=None):
    if now is None:
        now = datetime.datetime.now()
    calendar = timetable.get("odpt:calendar", "")
    direction = direction_label(timetable.get("odpt:busDirection", []))
    pole = timetable.get("odpt:busstopPole", "").split(".")[-1]
    route = ", ".join(timetable.get("odpt:busroute", []))
    note = timetable.get("odpt:note", "")
    departures = timetable.get("odpt:busstopPoleTimetableObject", [])

    if not full:
        if calendar != current_calendar():
            return
        upcoming = upcoming_departures(departures, now)
        if not upcoming:
            return
        print(f"\n{'='*60}")
        print(f"Pole:      {pole}  |  Direction: {direction}")
        print(f"{'='*60}")
        print(f"Upcoming departures (next 60 min from {now.strftime('%H:%M')}):")
        for dep_time, dep in upcoming:
            dest = dep.get("odpt:destinationBusstopPole", "").split(".")[-1]
            print(f"  {dep_time.strftime('%H:%M')}  → {dest}")
        return

    print(f"\n{'='*60}")
    print(f"Pole:      {pole}")
    print(f"Route:     {route}")
    print(f"Direction: {direction}")
    print(f"Calendar:  {calendar}")
    if note:
        print(f"Note:      {note}")
    print(f"{'='*60}")

    by_hour = {}
    for dep in departures:
        t = dep.get("odpt:departureTime", "")
        hour, minute = t.split(":") if ":" in t else ("?", t)
        by_hour.setdefault(hour, []).append(minute)

    for hour in sorted(by_hour):
        minutes = "  ".join(sorted(by_hour[hour]))
        print(f"  {hour}:  {minutes}")


def main():
    parser = argparse.ArgumentParser(description="Tamagawaonshitsumura bus timetable")
    parser.add_argument("--full", action="store_true", help="Print full schedule instead of next-hour departures")
    args = parser.parse_args()

    print(f"Fetching timetables for {STOP_NAME}...")
    timetables = build_timetables(CONSUMER_KEY, STOP_NAME)

    now = datetime.datetime.now()
    print(f"\nCurrent time: {now.strftime('%A %Y-%m-%d %H:%M')}")

    for timetable in timetables.values():
        print_timetable(timetable, full=args.full, now=now)


if __name__ == "__main__":
    main()
