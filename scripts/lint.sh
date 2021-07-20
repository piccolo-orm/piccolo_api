#!/bin/bash

SOURCES="piccolo_api tests"

isort $SOURCES
black $SOURCES
flake8 $SOURCES
# mypy $SOURCES
