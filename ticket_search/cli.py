import os
from datetime import datetime, timedelta

from .config import ROUTE, DEFAULT_YEAR, TARGET_CLASSES, MAX_RESULTS, MIN_LAYOVER, MAX_LAYOVER
from .models import format_duration
from .display import print_segment_header, print_flight_table, format_itinerary
from .solver import find_valid_itineraries
from .browser import BrowserSession


def _select_from_found(found: list[dict], flights: list[dict]):
    """Let user choose which flights to add from a found list."""
    classes_label = "/".join(TARGET_CLASSES)
    print(f"\n    ✓ 找到 {len(found)} 个{classes_label}舱可用航班:")
    print_flight_table(found)

    while True:
        sel = input(f"\n  添加哪些? (a=全部 / 1,3,5=指定编号 / n=不添加): ").strip().lower()
        if sel == "a":
            flights.extend(found)
            print(f"    ✓ 已添加全部 {len(found)} 个方案")
            return
        elif sel == "n":
            return
        else:
            try:
                indices = [int(x.strip()) - 1 for x in sel.split(",")]
                added = 0
                for idx in indices:
                    if 0 <= idx < len(found):
                        flights.append(found[idx])
                        added += 1
                if added:
                    print(f"    ✓ 已添加 {added} 个方案")
                    return
                else:
                    print("    ⚠ 无效编号")
            except ValueError:
                print("    ⚠ 请输入 a / n / 逗号分隔的编号")


def _collect_segment(origin: str, dest: str, browser: BrowserSession) -> list[dict]:
    """Collect flight options for a segment via browser capture."""
    flights: list[dict] = []

    while True:
        found = browser.wait_for_search(origin, dest)
        if found:
            _select_from_found(found, flights)

        if flights:
            print(f"\n  当前已有 {len(flights)} 个方案，继续搜索还是完成此段?")
            print("    c = 继续搜索更多航班")
            print("    d = 完成此段")
            while True:
                choice = input("  > ").strip().lower()
                if choice in ("c", "d"):
                    break
                print("    请输入 c 或 d")
            if choice == "d":
                break

    return flights


def _show_results(all_segments, valid) -> str | None:
    """Display search results or bottleneck analysis. Returns file path if saved."""
    if not valid:
        print("\n  ✗ 未找到满足转机时间限制的方案。")
        print("  请检查各段航班的时间安排。\n")

        print("  各段转机瓶颈分析:")
        for i in range(len(all_segments) - 1):
            seg_a = all_segments[i]
            seg_b = all_segments[i + 1]
            min_lay = None
            for fa in seg_a:
                for fb in seg_b:
                    layover = fb["departure"] - fa["arrival"]
                    if layover >= timedelta(0):
                        if min_lay is None or layover < min_lay:
                            min_lay = layover
            if min_lay is None:
                print(f"    {ROUTE[i+1]}: 所有方案到达时间均晚于下一段出发时间 ✗")
            elif min_lay > MAX_LAYOVER:
                print(f"    {ROUTE[i+1]}: 最短转机 {format_duration(min_lay)} (超过{int(MAX_LAYOVER.total_seconds()//3600)}h) ✗")
            elif min_lay < MIN_LAYOVER:
                print(f"    {ROUTE[i+1]}: 最短转机 {format_duration(min_lay)} (不足{int(MIN_LAYOVER.total_seconds()//60)}min) ⚠")
            else:
                print(f"    {ROUTE[i+1]}: 最短转机 {format_duration(min_lay)} ✓")
        return None

    truncated = len(valid) >= MAX_RESULTS
    min_min = int(MIN_LAYOVER.total_seconds() // 60)
    max_hr = int(MAX_LAYOVER.total_seconds() // 3600)

    summary = (f"✓ 找到 {'≥' if truncated else ''}{len(valid)} 个可行方案"
               f"（所有转机 {min_min}min~{max_hr}h）")
    print(f"\n  {summary}")
    if truncated:
        print(f"    (结果已截断，仅显示前 {MAX_RESULTS} 个)")
    print()

    file_parts: list[str] = []
    route_display = " → ".join(ROUTE)
    file_parts.append(f"路线: {route_display}")
    file_parts.append(f"筛选舱位: {'/'.join(TARGET_CLASSES)}")
    file_parts.append(f"转机限制: {min_min}min ≤ 转机 ≤ {max_hr}h")
    file_parts.append(f"{summary}\n")

    for idx, itin in enumerate(valid, 1):
        text = format_itinerary(itin, idx)
        file_parts.append(text)

    os.makedirs("results", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results/itineraries_{ts}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(file_parts) + "\n")

    print(f"\n  ✓ 结果已保存至 {filename}")
    return filename


def run():
    """Main CLI entry point."""
    print("=" * 60)
    print("        ✈  多段机票路线可行性搜索工具  ✈")
    print("=" * 60)
    route_display = " → ".join(ROUTE)
    print(f"\n  路线: {route_display}")
    print(f"  共 {len(ROUTE) - 1} 段航程")
    print(f"  默认年份: {DEFAULT_YEAR}")
    classes_label = "/".join(TARGET_CLASSES)
    print(f"  筛选舱位: {classes_label}")
    min_min = int(MIN_LAYOVER.total_seconds() // 60)
    max_hr = int(MAX_LAYOVER.total_seconds() // 3600)
    print(f"  转机时间限制: {min_min}分钟 ≤ 转机 ≤ {max_hr}小时")

    n_segments = len(ROUTE) - 1

    print(f"\n  搜索顺序:")
    print(f"    f = 正序 (第1段 → 第{n_segments}段)")
    print(f"    r = 倒序 (第{n_segments}段 → 第1段)")
    while True:
        order = input("  > ").strip().lower()
        if order in ("f", "r"):
            break
        print("    请输入 f 或 r")

    reverse = order == "r"
    search_order = list(range(n_segments))
    if reverse:
        search_order.reverse()

    browser = BrowserSession()
    try:
        print("\n  正在启动浏览器...")
        browser.start()
        print("  ✓ 浏览器已启动")
        input("  请在浏览器中登录 ExpertFlyer，完成后按回车继续...")

        all_segments: list[list[dict] | None] = [None] * n_segments
        collected = 0

        for i in search_order:
            origin, dest = ROUTE[i], ROUTE[i + 1]
            print_segment_header(i, origin, dest)
            flights = _collect_segment(origin, dest, browser)

            if not flights:
                print(f"\n  ⚠ 第 {i+1} 段没有添加任何方案，无法继续。")
                return

            print(f"\n  第 {i+1} 段最终方案汇总:")
            print_flight_table(flights)
            all_segments[i] = flights
            collected += 1

            total_combos = 1
            for seg in all_segments:
                if seg is not None:
                    total_combos *= len(seg)
            print(f"\n  已完成 {collected}/{n_segments} 段，当前共 {total_combos} 种组合")

        print(f"\n\n{'='*60}")
        print("  正在剪枝并搜索可行方案...")
        print(f"{'='*60}")

        total = 1
        for seg in all_segments:
            total *= len(seg)
        print(f"\n  原始总组合数: {total}")

        valid = find_valid_itineraries(all_segments)
        _show_results(all_segments, valid)

        print(f"\n{'='*60}")
        print("  搜索完成")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\n  ⚠ 错误: {e}")
    finally:
        browser.close()
