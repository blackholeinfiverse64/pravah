def generate_infra_signals(trace_id, latency):
    return [
        ("pod_crash", "kubernetes", "restart_count", 1)
    ]