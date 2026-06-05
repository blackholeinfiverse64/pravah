from collections import defaultdict

def aggregate_signals(signals):
    seen = set()
    unique = []

    for s in signals:
        key = (s["signal_type"], s["metric"], s["timestamp"], s["trace_id"])
        if key not in seen:
            seen.add(key)
            unique.append(s)

    # sort by timestamp
    unique.sort(key=lambda x: x["timestamp"])

    grouped = defaultdict(list)
    for s in unique:
        grouped[s["trace_id"]].append(s)

    return dict(grouped)