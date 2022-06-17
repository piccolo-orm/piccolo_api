#!/bin/bash
sphinx-autobuild -a docs/source docs/build/html --re-ignore=docs/source/_build/ --watch piccolo_api
