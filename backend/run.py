import os

import uvicorn


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "7999")))
    
    # Robust module detection for Render (works if root is / or /backend)
    module_path = "backend.app.main:app" if os.path.exists("backend/app/main.py") else "app.main:app"
    
    uvicorn.run(module_path, host="0.0.0.0", port=port, reload=False)
