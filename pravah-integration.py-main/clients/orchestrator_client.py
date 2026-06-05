class OrchestratorClient:
    async def execute_action(self, deployment_id: str, action: str):
        return {"success": True, "action": action, "deployment_id": deployment_id}
