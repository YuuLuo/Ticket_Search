from datetime import timedelta

from .config import ROUTE, TARGET_CLASSES
from .models import format_duration


def format_class_seats(class_seats: list[dict[str, int]]) -> str:
    """Format class availability like 'Y9/9 E2/2 V3/3' or 'Y9 E2 V3'."""
    if not class_seats:
        return ""
    parts = []
    for cls in TARGET_CLASSES:
        values = [str(s.get(cls, 0)) for s in class_seats]
        parts.append(f"{cls}{'/'.join(values)}")
    return " ".join(parts)


def print_segment_header(index: int, origin: str, dest: str):
    total = len(ROUTE) - 1
    print(f"\n{'='*60}")
    print(f"  第 {index + 1}/{total} 段: {origin} → {dest}")
    print(f"{'='*60}")


def print_flight_table(flights: list[dict]):
    has_flight_info = any(f.get("flights") for f in flights)
    seats_label = "/".join(TARGET_CLASSES)
    if has_flight_info:
        print(f"\n  {'#':^4} {'出发':^14} {'到达':^14} {'航班':^20} {seats_label:^16}")
        print(f"  {'-'*4} {'-'*14} {'-'*14} {'-'*20} {'-'*16}")
        for i, f in enumerate(flights, 1):
            dep = f["departure"]
            arr = f["arrival"]
            fl = f.get("flights", "")
            cs = f.get("class_seats", [])
            cs_str = format_class_seats(cs)
            print(
                f"  {i:^4} "
                f"{dep.strftime('%m-%d %H:%M'):^14} "
                f"{arr.strftime('%m-%d %H:%M'):^14} "
                f"{fl:^20} "
                f"{cs_str:^16}"
            )
    else:
        print(f"\n  {'#':^4} {'出发':^14} {'到达':^14}")
        print(f"  {'-'*4} {'-'*14} {'-'*14}")
        for i, f in enumerate(flights, 1):
            dep = f["departure"]
            arr = f["arrival"]
            print(
                f"  {i:^4} "
                f"{dep.strftime('%m-%d %H:%M'):^14} "
                f"{arr.strftime('%m-%d %H:%M'):^14}"
            )


def format_itinerary(itinerary: list[dict], index: int) -> str:
    """Format an itinerary into a string. Also prints it."""
    lines: list[str] = []

    def out(s: str = ""):
        lines.append(s)

    out(f"\n{'#'*70}")
    out(f"  方案 {index}")
    out(f"{'#'*70}")

    total_layover = timedelta()
    seats_label = "/".join(TARGET_CLASSES)

    out(f"\n  {'段':^4} {'航段':^10} {'出发':^14} {'到达':^14} {'转机':^8} {'航班':^20} {seats_label}")
    out(f"  {'-'*4} {'-'*10} {'-'*14} {'-'*14} {'-'*8} {'-'*20} {'-'*len(seats_label)}")

    for i, flight in enumerate(itinerary):
        dep = flight["departure"]
        arr = flight["arrival"]

        layover_str = ""
        if i > 0:
            prev_arr = itinerary[i - 1]["arrival"]
            layover = dep - prev_arr
            total_layover += layover
            layover_str = format_duration(layover)

        seg_label = f"{flight['origin']}→{flight['dest']}"
        fl = flight.get("flights", "")
        cs = flight.get("class_seats", [])
        cs_str = format_class_seats(cs)

        out(
            f"  {i+1:^4} {seg_label:^10} "
            f"{dep.strftime('%m-%d %H:%M'):^14} "
            f"{arr.strftime('%m-%d %H:%M'):^14} "
            f"{layover_str:^8} "
            f"{fl:^20} "
            f"{cs_str}"
        )

        connections = flight.get("connections", [])
        if connections:
            for conn in connections:
                arr_t = conn["arrive"].strftime("%m-%d %H:%M")
                dep_t = conn["depart"].strftime("%m-%d %H:%M")
                wait = conn["depart"] - conn["arrive"]
                out(f"         ↳ 经停 {conn['airport']}  "
                    f"到达 {arr_t} → 出发 {dep_t}  "
                    f"等待 {format_duration(wait)}")

    overall = itinerary[-1]["arrival"] - itinerary[0]["departure"]
    min_seats = _min_class_seats(itinerary)

    out(f"\n  总转机等待: {format_duration(total_layover)}")
    out(f"  总行程时长: {format_duration(overall)}")
    out(f"  行程日期:   {itinerary[0]['departure'].strftime('%m-%d')} → "
        f"{itinerary[-1]['arrival'].strftime('%m-%d')}")
    out(f"  最低余票:   {min_seats}")

    text = "\n".join(lines)
    print(text)
    return text


def _min_class_seats(itinerary: list[dict]) -> str:
    """Return the minimum seat count per class across all sub-segments."""
    mins: dict[str, int] = {cls: float("inf") for cls in TARGET_CLASSES}
    for flight in itinerary:
        for seg_seats in flight.get("class_seats", []):
            for cls in TARGET_CLASSES:
                v = seg_seats.get(cls, 0)
                if v < mins[cls]:
                    mins[cls] = v
    parts = []
    for cls in TARGET_CLASSES:
        v = int(mins[cls]) if mins[cls] != float("inf") else 0
        parts.append(f"{cls}{v}")
    return " ".join(parts)


def print_itinerary(itinerary: list[dict], index: int):
    """Backward-compatible wrapper."""
    format_itinerary(itinerary, index)
