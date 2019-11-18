Token Auth
==========

Introduction
------------

Token auth is a simple approach to authentication, which is most suitable for
mobile apps and embedded systems.

Each user / client has a token generated for them. The token is just a random
string - no information is embedded within it, as is the case with JWT.

When a client makes a request, the token needs to be added as a header. The
user object associated with this token is then retrieved from a
'token provider'. By default, this is a Piccolo table, but you can implement
your own token provider if you so choose.

The token doesn't expire. It's suitable for mobile apps where tokens can be
securely stored on the device. The client logic is simple to implement, as you
don't have to worry about refreshing your token.

It's not recommended to use this type of authentication with web apps, because
you can't securely store the token using Javascript, which makes it
susceptible to exposure using a XSS attack.
