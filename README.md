![Logo](https://github.com/piccolo-orm/piccolo_api/raw/master/docs/logo_hero.png "Piccolo API Logo")

![Tests](https://github.com/piccolo-orm/piccolo_api/actions/workflows/tests.yaml/badge.svg)
![Release](https://github.com/piccolo-orm/piccolo_api/actions/workflows/release.yaml/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/piccolo-api/badge/?version=latest)](https://piccolo-api.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/piccolo-api?color=%2334D058&label=pypi)](https://pypi.org/project/piccolo-api/)
[![codecov](https://codecov.io/gh/piccolo-orm/piccolo_api/branch/master/graph/badge.svg?token=JJ5326P7FT)](https://codecov.io/gh/piccolo-orm/piccolo_api)

# Piccolo API

Utilities for easily exposing [Piccolo](https://piccolo-orm.readthedocs.io/en/latest/) tables as REST endpoints in ASGI apps, such as [Starlette](https://www.starlette.io) and [FastAPI](https://fastapi.tiangolo.com/).

Includes a bunch of useful ASGI middleware:

- Session Auth
- Token Auth
- Rate Limiting
- CSRF
- Content Security Policy (CSP)
- And more

It also contains excellent Pydantic support, allowing you to easily create Pydantic models based on your Piccolo tables.

You can read the docs [here](https://piccolo-api.readthedocs.io/en/latest/).
