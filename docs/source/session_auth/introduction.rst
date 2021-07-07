Introduction
============

Session auth is the classic approach to authentication on the web. When a user
logs in, a session cookie is set on their browser, which contains a unique
session ID. This session ID is also stored by the server in a
database. Each time the user makes a request, the session ID stored in the
cookie is compared with the ones stored in the database, to check if the user
has a valid session.

There are several advantages to session auth:

 * A session can be invalidated at any time, by deleting a session from the database.
 * HTTP-only cookies are immune to tampering with Javascript.
