#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import os
import typing as t

from setuptools import find_packages, setup

from piccolo_api import __VERSION__ as VERSION

directory = os.path.abspath(os.path.dirname(__file__))


with open(os.path.join(directory, "requirements/requirements.txt")) as f:
    contents = f.read()
    REQUIREMENTS = [i.strip() for i in contents.strip().split("\n")]


with open(os.path.join(directory, "README.md")) as f:
    LONG_DESCRIPTION = f.read()


EXTRAS = ["s3"]


def parse_requirement(req_path: str) -> t.List[str]:
    """
    Parses a requirement file - returning a list of contents.
    Example::
        parse_requirement('requirements.txt')       # requirements/requirements.txt
        parse_requirement('extras/s3.txt')  # requirements/extras/playground.txt
    :returns: A list of requirements specified in the file.
    """  # noqa: E501
    with open(os.path.join(directory, "requirements", req_path)) as f:
        contents = f.read()
        return [i.strip() for i in contents.strip().split("\n")]


def extras_require() -> t.Dict[str, t.List[str]]:
    """
    Parse requirements in requirements/extras directory
    """
    extra_requirements = {
        extra: parse_requirement(os.path.join("extras", f"{extra}.txt"))
        for extra in EXTRAS
    }

    extra_requirements["all"] = list(
        itertools.chain.from_iterable(extra_requirements.values())
    )

    return extra_requirements


setup(
    name="piccolo_api",
    version=VERSION,
    description=(
        "Utilities for using the Piccolo ORM in ASGI apps, plus essential "
        "ASGI middleware such as authentication and rate limiting."
    ),
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Daniel Townsend",
    author_email="dan@dantownsend.co.uk",
    python_requires=">=3.7.0",
    url="https://github.com/piccolo-orm/piccolo_api",
    packages=find_packages(exclude=("tests",)),
    package_data={
        "": [
            "templates/*",
        ],
        "piccolo_api": ["py.typed"],
    },
    install_requires=REQUIREMENTS,
    extras_require=extras_require(),
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
)
