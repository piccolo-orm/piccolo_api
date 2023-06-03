import os
import sys

import uvicorn

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
        )
    ),
)


if __name__ == "__main__":
    from app import app
    from tables import Movie

    Movie.create_table(if_not_exists=True).run_sync()
    uvicorn.run(app, port=8081)
