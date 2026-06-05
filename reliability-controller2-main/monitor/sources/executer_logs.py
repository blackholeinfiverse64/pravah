def generate_executer_signals(trace_id):
    return [
        ("execution_failure", "executer", "status", "FAILURE")
    ]