def classify_signal(metric, value):

    rules = {
        "cpu": [(85, "CRITICAL"), (60, "WARN"), (0, "INFO")],
        "memory": [(80, "CRITICAL"), (60, "WARN"), (0, "INFO")],
        "latency": [(700, "CRITICAL"), (400, "WARN"), (0, "INFO")],
        "error_rate": [(0.5, "CRITICAL"), (0.2, "WARN"), (0, "INFO")]
    }

    if metric not in rules:
        return "INFO"

    for threshold, severity in rules[metric]:
        if value > threshold:
            return severity

    return "INFO"