#!/usr/bin/env python
from livereload import Server, shell


server = Server()
server.watch(
    'source/',
    shell('make html')
)
server.watch(
    '../piccolo_api',
    shell('make html')
)
server.serve(root='build/html')

