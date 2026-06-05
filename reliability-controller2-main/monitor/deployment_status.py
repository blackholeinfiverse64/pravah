from datetime import datetime

def get_deployment_status():
    return {
        "status": "success",  # change to failed for testing
        "version": "latest",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "rollback": False
    }