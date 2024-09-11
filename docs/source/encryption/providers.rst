Providers
=========

.. currentmodule:: piccolo_api.encryption.providers

``EncryptionProvider``
----------------------

.. autoclass:: EncryptionProvider

``FernetProvider``
------------------

.. autoclass:: FernetProvider

``PlainTextProvider``
---------------------

.. autoclass:: PlainTextProvider

``XChaCha20Provider``
---------------------

.. autoclass:: XChaCha20Provider

-------------------------------------------------------------------------------

Dependencies
------------

When first using some of the providers, you will be prompted to install the
underlying encryption library.

For example, with ``XChaCha20Provider``, you need to install ``pynacl`` as
follows:

.. code-block:: bash

    pip install piccolo_api[pynacl]

-------------------------------------------------------------------------------

Example usage
-------------

All of the providers work the same (except their parameters may be different).

Here's an example using ``XChaCha20Provider``:

.. code-block:: python

    >>> from piccolo_api.encryption.providers import XChaCha20Provider

    >>> encryption_key = XChaCha20Provider.get_new_key()
    >>> provider = XChaCha20Provider(encryption_key=encryption_key)

    >>> encrypted = provider.encrypt("hello world")
    >>> print(provider.decrypt(encrypted))
    "hello world"

-------------------------------------------------------------------------------

Which provider to use?
----------------------

``XChaCha20Provider`` is the most secure.

You may decide to use ``FernetProvider`` if you already have the Python
``cryptography`` library as a dependency in your project.

-------------------------------------------------------------------------------

Passing in encryption keys via environment variables
----------------------------------------------------

A common way of passing sensitive information to an app is via environment
variables.

The encryption keys for ``XChaCha20Provider`` and ``FernetProvider`` are in
bytes. You can still pass them in as environment variables though.

One approach (using ``XChaCha20Provider`` as an example), is to convert the
bytes to a hex string:

.. code-block:: python

    >>> key = XChaCha20Provider.get_new_key()
    >>> key.hex()
    '25d49a31af520fd4c24553890f154deeead1fb61a409e6ea3df7b62ed4b8925d'

You can then use the hex string as the environment variable. To convert it back
into bytes:

.. code-block:: python

    >>> key = bytes.fromhex('25d49a31af520fd4c24553890f154deeead1fb61a409e6ea3df7b62ed4b8925d')
