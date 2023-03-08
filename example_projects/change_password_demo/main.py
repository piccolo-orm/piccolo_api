import os
import sys

# Modify the path, so piccolo_api is available
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


if __name__ == "__main__":

    import uvicorn

    uvicorn.run("app:app", reload=True)
