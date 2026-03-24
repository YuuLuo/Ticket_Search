import json
import re
from datetime import datetime

from .config import DEFAULT_YEAR, TARGET_CLASSES


def parse_api_datetime(dt_str: str, date_str: str) -> datetime:
    """Parse API datetime like '06-22T06:00' with year from date '2026-06-22'."""
    match = re.match(r"(\d{2})-(\d{2})T(\d{2}):(\d{2})", dt_str)
    if not match:
        raise ValueError(f"无法解析API时间: {dt_str}")
    month, day, hour, minute = (int(x) for x in match.groups())
    year = int(date_str[:4]) if date_str else DEFAULT_YEAR
    return datetime(year, month, day, hour, minute)


def get_class_availability(segment: dict, cls: str) -> int:
    for bc in segment.get("bookingClassAvailability", []):
        if bc["code"] == cls:
            return bc.get("availability", 0)
    return 0


def itinerary_has_classes(itinerary: dict, classes: str) -> bool:
    """All segments must have availability > 0 for every class in `classes`."""
    for seg in itinerary.get("segments", []):
        for cls in classes:
            if get_class_availability(seg, cls) <= 0:
                return False
    return True


def extract_json_from_text(raw_text: str) -> str | None:
    """Extract the searchResults JSON string from raw API response text."""
    for line in raw_text.strip().split("\n"):
        m = re.match(r"\d+:(.*)", line.strip())
        if m and "searchResults" in m.group(1):
            return m.group(1)

    if "searchResults" in raw_text:
        try:
            start = raw_text.index("{", raw_text.index("searchResults") - 2)
        except ValueError:
            return None
        depth = 0
        for i, ch in enumerate(raw_text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return raw_text[start:i + 1]
    return None


def _seg_class_seats(segment: dict, classes: str) -> dict[str, int]:
    """Get availability for each target class in a segment."""
    return {cls: get_class_availability(segment, cls) for cls in classes}


def extract_flights_from_api(raw_text: str, origin: str, dest: str) -> list[dict]:
    """Parse API response text and extract flights with target class availability."""
    json_str = extract_json_from_text(raw_text)
    if not json_str:
        print("    ⚠ 未找到有效的 searchResults JSON")
        return []

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"    ⚠ JSON解析失败: {e}")
        return []

    departure_list = data.get("searchResults", {}).get("departure", [])
    flights = []

    for date_entry in departure_list:
        date_str = date_entry.get("date", "")
        itineraries = date_entry.get("data", {}).get("itineraries", [])

        for itin in itineraries:
            if not itinerary_has_classes(itin, TARGET_CLASSES):
                continue

            segments = itin.get("segments", [])
            if not segments:
                continue

            first_seg = segments[0]
            last_seg = segments[-1]

            if first_seg["departureAirport"] != origin or last_seg["arrivalAirport"] != dest:
                continue

            dep_dt = parse_api_datetime(first_seg["departureDateTime"], date_str)
            arr_dt = parse_api_datetime(last_seg["arrivalDateTime"], date_str)

            flight_nums = []
            class_seats: list[dict[str, int]] = []
            sub_segments = []
            for seg in segments:
                airline = seg.get("marketingAirlineCode", "")
                fnum = seg.get("flightNumber", "")
                flight_nums.append(f"{airline}{fnum}")
                seats = _seg_class_seats(seg, TARGET_CLASSES)
                class_seats.append(seats)
                sub_segments.append({
                    "origin": seg["departureAirport"],
                    "dest": seg["arrivalAirport"],
                    "flight": f"{airline}{fnum}",
                    "departure": parse_api_datetime(seg["departureDateTime"], date_str),
                    "arrival": parse_api_datetime(seg["arrivalDateTime"], date_str),
                    "class_seats": seats,
                })

            connections = []
            for ci in range(len(sub_segments) - 1):
                connections.append({
                    "airport": sub_segments[ci]["dest"],
                    "arrive": sub_segments[ci]["arrival"],
                    "depart": sub_segments[ci + 1]["departure"],
                })

            flight = {
                "origin": origin,
                "dest": dest,
                "departure": dep_dt,
                "arrival": arr_dt,
                "flights": "/".join(flight_nums),
                "class_seats": class_seats,
                "num_segments": len(segments),
                "sub_segments": sub_segments,
                "connections": connections,
            }
            flights.append(flight)

    return flights
