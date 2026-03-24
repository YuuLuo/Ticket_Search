from datetime import timedelta

from .config import ROUTE, MIN_LAYOVER, MAX_LAYOVER, MAX_RESULTS


def find_valid_itineraries(all_segments: list[list[dict]]) -> list[list[dict]]:
    n = len(all_segments)
    if n == 0:
        return []

    # Build adjacency — compatible[i][a] = set of valid indices in segment i+1
    compatible = []
    for i in range(n - 1):
        fwd: dict[int, set[int]] = {}
        for a, fa in enumerate(all_segments[i]):
            fwd[a] = set()
            for b, fb in enumerate(all_segments[i + 1]):
                layover = fb["departure"] - fa["arrival"]
                if MIN_LAYOVER <= layover <= MAX_LAYOVER:
                    fwd[a].add(b)
        compatible.append(fwd)

    # Forward + backward pruning (arc consistency)
    reachable = [set(range(len(seg))) for seg in all_segments]

    for i in range(n - 1):
        next_ok = set()
        curr_ok = set()
        for a in reachable[i]:
            nexts = compatible[i][a] & reachable[i + 1]
            if nexts:
                curr_ok.add(a)
                next_ok |= nexts
            compatible[i][a] = nexts
        reachable[i] = curr_ok
        reachable[i + 1] = next_ok

    for i in range(n - 2, -1, -1):
        curr_ok = set()
        for a in reachable[i]:
            nexts = compatible[i][a] & reachable[i + 1]
            if nexts:
                curr_ok.add(a)
            compatible[i][a] = nexts
        reachable[i] = curr_ok

    # Report pruning results
    print("\n  剪枝后各段剩余方案:")
    pruned_total = 1
    for i in range(n):
        cnt = len(reachable[i])
        pruned_total *= cnt if cnt else 1
        orig = len(all_segments[i])
        label = f"{ROUTE[i]}→{ROUTE[i+1]}"
        print(f"    {label:>10}: {cnt}/{orig} 个航班可达")
    print(f"  剪枝后最大搜索空间: {pruned_total}")

    if any(len(r) == 0 for r in reachable):
        return []

    # DFS enumeration with cap
    valid: list[list[dict]] = []

    def dfs(seg_idx: int, path: list[int]):
        if len(valid) >= MAX_RESULTS:
            return
        if seg_idx == n:
            valid.append([all_segments[i][path[i]] for i in range(n)])
            return
        candidates = reachable[seg_idx] if seg_idx == 0 else compatible[seg_idx - 1][path[seg_idx - 1]]
        for f_idx in sorted(candidates):
            path.append(f_idx)
            dfs(seg_idx + 1, path)
            path.pop()
            if len(valid) >= MAX_RESULTS:
                return

    dfs(0, [])
    return valid
