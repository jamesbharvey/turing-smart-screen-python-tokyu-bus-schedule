import datetime
import hashlib
import json
import pathlib
import time
import requests

API_BASE = "https://api.odpt.org/api/v4"
CACHE_DIR = pathlib.Path.home() / ".cache" / "odpt"
CACHE_TTL = 24 * 60 * 60  # seconds

CALENDAR_MERGE = {
    "Saturday": "Saturday/Sunday/Holiday",
    "Sunday":   "Saturday/Sunday/Holiday",
}


def fetch(consumer_key, endpoint, params):
    params = dict(params)
    params["acl:consumerKey"] = consumer_key
    cache_key = hashlib.md5((endpoint + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    cache_file = CACHE_DIR / f"{cache_key}.json"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < CACHE_TTL:
        return json.loads(cache_file.read_text())

    r = requests.get(f"{API_BASE}/{endpoint}", params=params)
    r.raise_for_status()
    data = r.json()
    cache_file.write_text(json.dumps(data))
    return data


def get_poles(consumer_key, stop_name, route_filter=None):
    """Return BusstopPole records for the given stop name (case-insensitive substring match).

    Args:
        consumer_key: ODPT API consumer key.
        stop_name: Substring to match against owl:sameAs (e.g. "Tamagawaonshitsumura").
        route_filter: Optional substring to require in at least one timetable ID (e.g. "Tama11").

    Returns:
        List of matching pole dicts.
    """
    results = fetch(consumer_key, "odpt:BusstopPole", {
        "odpt:operator": "odpt.Operator:TokyuBus",
    })
    poles = [p for p in results if stop_name.lower() in p.get("owl:sameAs", "").lower()]
    if route_filter:
        poles = [
            p for p in poles
            if any(route_filter.lower() in t.lower() for t in p.get("odpt:busstopPoleTimetable", []))
        ]
    return poles


def get_timetable(consumer_key, timetable_id):
    """Fetch a single BusstopPoleTimetable by its owl:sameAs ID.

    Returns:
        Timetable dict, or None if not found.
    """
    results = fetch(consumer_key, "odpt:BusstopPoleTimetable", {
        "owl:sameAs": timetable_id,
    })
    return results[0] if results else None


def calendar_label(calendar_id):
    """Normalise a calendar ID to a display label, merging Saturday/Sunday."""
    label = calendar_id.split(":")[-1] if calendar_id else calendar_id
    return CALENDAR_MERGE.get(label, label)


def direction_label(direction_ids):
    """Return a human-readable direction string from a list of direction IDs."""
    if not direction_ids:
        return ""
    return ", ".join(d.split(".")[-1] for d in direction_ids)


def current_calendar():
    """Return 'Weekday' or 'Saturday/Sunday/Holiday' based on today's date."""
    return "Weekday" if datetime.date.today().weekday() < 5 else "Saturday/Sunday/Holiday"


def upcoming_departures(departures, now, window_minutes=60):
    """Return departures within window_minutes of now, sorted by time.

    Args:
        departures: List of timetable object dicts.
        now: datetime.datetime representing the current time.
        window_minutes: How many minutes ahead to look.

    Returns:
        List of (departure_datetime, dep_dict) tuples.
    """
    cutoff = now + datetime.timedelta(minutes=window_minutes)
    results = []
    for dep in departures:
        time_str = dep.get("odpt:departureTime", "")
        if ":" not in time_str:
            continue
        h, m = time_str.split(":")
        dep_time = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
        if now <= dep_time <= cutoff:
            results.append((dep_time, dep))
    return sorted(results, key=lambda x: x[0])


def build_timetables(consumer_key, stop_name, route_filter=None):
    """Fetch and merge timetables for a stop, collapsing Saturday/Sunday into one bucket.

    Args:
        consumer_key: ODPT API consumer key.
        stop_name: Stop name substring (e.g. "Tamagawaonshitsumura").
        route_filter: Optional route substring to restrict results (e.g. "Tama11").

    Returns:
        Dict mapping (pole_id, calendar_label) -> merged timetable dict.
        Timetable dicts have odpt:calendar set to the merged label.
    """
    poles = get_poles(consumer_key, stop_name, route_filter)

    timetable_ids = []
    for pole in poles:
        ids = pole.get("odpt:busstopPoleTimetable", [])
        if route_filter:
            ids = [t for t in ids if route_filter.lower() in t.lower()]
        timetable_ids.extend(ids)

    merged = {}
    for tid in timetable_ids:
        timetable = get_timetable(consumer_key, tid)
        if not timetable:
            continue
        cal = calendar_label(timetable.get("odpt:calendar", ""))
        pole_id = timetable.get("odpt:busstopPole", "")
        key = (pole_id, cal)
        if key not in merged:
            merged[key] = timetable
            merged[key]["odpt:calendar"] = cal
        else:
            existing = {
                d["odpt:departureTime"]
                for d in merged[key].get("odpt:busstopPoleTimetableObject", [])
            }
            for dep in timetable.get("odpt:busstopPoleTimetableObject", []):
                if dep["odpt:departureTime"] not in existing:
                    merged[key]["odpt:busstopPoleTimetableObject"].append(dep)
                    existing.add(dep["odpt:departureTime"])

    return merged
