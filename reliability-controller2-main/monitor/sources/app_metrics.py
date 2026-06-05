def generate_app_signals(trace_id, latency, error_rate):
    return [
        ("latency_spike", "application", "latency", latency),
        ("error_spike", "application", "error_rate", error_rate)
    ]