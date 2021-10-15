Introduction
============

CSRF (`Cross Site Request Forgery <https://owasp.org/www-community/attacks/csrf>`_ )
is a serious security vulnerability for websites which are relying on cookies
for authentication.

Browsers will send cookies belonging to a domain, no matter which website the
request was made from. So if you're authenticated on foo.com, an attacker can
make malicious HTTP requests to foo.com on your behalf even when you're
browsing a completely different website.

-------------------------------------------------------------------------------

Make sure safe methods are safe!
--------------------------------

The CSRF protection only works on unsafe methods - DELETE, POST, PUT etc.

Make sure that safe methods (e.g. GET) are indeed safe, meaning they do not
cause state to change (i.e. adding data to the database, or other side
effects).
