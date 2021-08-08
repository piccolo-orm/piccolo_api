"""
Used for serving the example session app, so we can manually test it.
"""

if __name__ == "__main__":
    import os
    import sys

    import uvicorn  # type: ignore
    from session_auth.test_session import APP  # type: ignore

    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    uvicorn.run(APP, port=8999)
