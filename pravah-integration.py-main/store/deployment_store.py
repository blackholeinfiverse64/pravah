class DeploymentStore:
    def __init__(self):
        self.deployments = []
    
    async def get_active_deployments(self):
        return self.deployments
    
    def add_deployment(self, deployment):
        self.deployments.append(deployment)
