from __future__ import annotations

import contextlib
import logging
import os
import pathlib
import shutil
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import IO, TYPE_CHECKING, Optional, Union

from piccolo.apps.user.tables import BaseUser
from piccolo.columns.column_types import Array, Text, Varchar

from .base import ALLOWED_CHARACTERS, ALLOWED_EXTENSIONS, MediaStorage

if TYPE_CHECKING:  # pragma: no cover
    from concurrent.futures._base import Executor


logger = logging.getLogger(__name__)


class LocalMediaStorage(MediaStorage):
    def __init__(
        self,
        column: Union[Text, Varchar, Array],
        media_path: str,
        executor: Optional[Executor] = None,
        allowed_extensions: Optional[Sequence[str]] = ALLOWED_EXTENSIONS,
        allowed_characters: Optional[Sequence[str]] = ALLOWED_CHARACTERS,
        file_permissions: Optional[int] = 0o600,
    ):
        """
        Stores media files on a local path. This is good for simple
        applications, where you're happy with the media files being stored
        on a single server.

        :param column:
            The Piccolo ``Column`` which the storage is for.
        :param media_path:
            This is the local folder where the media files will be stored. It
            should be an absolute path. For example,
            ``'/srv/piccolo-media/poster/'``.
        :param executor:
            An executor, which file save operations are run in, to avoid
            blocking the event loop. If not specified, we use a sensibly
            configured :class:`ThreadPoolExecutor <concurrent.futures.ThreadPoolExecutor>`.
        :param allowed_extensions:
            Which file extensions are allowed. If ``None``, then all extensions
            are allowed (not recommended unless the users are trusted).
        :param allowed_characters:
            Which characters are allowed in the file name. By default, it's
            very strict. If set to ``None`` then all characters are allowed.
        :param file_permissions:
            If set to a value other than ``None``, then all uploaded files are
            given these file permissions.
        """  # noqa: E501
        self.media_path = media_path
        self.executor = executor or ThreadPoolExecutor(max_workers=10)
        self.file_permissions = file_permissions

        if not os.path.exists(media_path):
            os.mkdir(self.media_path)

        super().__init__(
            column=column,
            allowed_extensions=allowed_extensions,
            allowed_characters=allowed_characters,
        )

    async def store_file(
        self, file_name: str, file: IO, user: Optional[BaseUser] = None
    ) -> str:
        return await self._run_sync(
            lambda: self.store_file_sync(
                file_name=file_name, file=file, user=user
            )
        )

    def store_file_sync(
        self, file_name: str, file: IO, user: Optional[BaseUser] = None
    ) -> str:
        """
        A sync version of :meth:`store_file`.
        """
        # If the file_name includes the entire path (e.g. /foo/bar.jpg) - we
        # just want bar.jpg.
        file_name = pathlib.Path(file_name).name

        file_key = self.generate_file_key(file_name=file_name, user=user)

        path = os.path.join(self.media_path, file_key)

        if os.path.exists(path):
            logger.error(
                "A file name clash has occurred - the chances are very "
                "low. Could be malicious, or a serious bug."
            )
            raise IOError("Unable to save the file")

        with open(path, "wb") as new_file:
            shutil.copyfileobj(file, new_file)
            if self.file_permissions is not None:
                os.chmod(path, self.file_permissions)

        return file_key

    async def generate_file_url(
        self, file_key: str, root_url: str, user: Optional[BaseUser] = None
    ) -> str:
        """
        This retrieves an absolute URL for the file.
        """
        return self.generate_file_url_sync(
            file_key=file_key, root_url=root_url, user=user
        )

    def generate_file_url_sync(
        self, file_key: str, root_url: str, user: Optional[BaseUser] = None
    ) -> str:
        """
        A sync version of :meth:`generate_file_url`.
        """
        return "/".join((root_url.rstrip("/"), file_key))

    ###########################################################################

    async def get_file(self, file_key: str) -> Optional[IO]:
        """
        Returns the file object matching the ``file_key``. The caller is
        responsible for closing it.
        """
        return await self._run_sync(
            lambda: self.get_file_sync(file_key=file_key)
        )

    def get_file_sync(self, file_key: str) -> Optional[IO]:
        """
        A sync version of :meth:`get_file`.
        """
        path = os.path.join(self.media_path, file_key)
        return open(path, "rb")

    async def delete_file(self, file_key: str):
        """
        Deletes the file object matching the ``file_key``.
        """
        return await self._run_sync(
            lambda: self.delete_file_sync(file_key=file_key)
        )

    def delete_file_sync(self, file_key: str):
        """
        A sync version of :meth:`delete_file`.
        """
        path = os.path.join(self.media_path, file_key)
        os.unlink(path)

    async def bulk_delete_files(self, file_keys: list[str]):
        await self._run_sync(
            lambda: self.bulk_delete_files_sync(file_keys=file_keys)
        )

    def bulk_delete_files_sync(self, file_keys: list[str]):
        """
        A sync version of :meth:`bulk_delete_files`.
        """
        media_path = self.media_path

        if file_keys and not os.path.isdir(media_path):
            # Otherwise every delete below is quietly skipped, and a missing
            # media folder looks like a successful clean up.
            raise FileNotFoundError(media_path)

        for file_key in file_keys:
            # A file which has already gone shouldn't abandon the rest of the
            # batch - the other backends behave this way too.
            with contextlib.suppress(FileNotFoundError):
                os.unlink(os.path.join(media_path, file_key))

    async def get_file_keys(self) -> list[str]:
        """
        Returns the file key for each file we have stored.
        """
        return await self._run_sync(self.get_file_keys_sync)

    def get_file_keys_sync(self) -> list[str]:
        """
        A sync version of :meth:`get_file_keys`.
        """
        file_keys: list[str] = []
        for _, _, filenames in os.walk(self.media_path):
            file_keys.extend(filenames)
            break

        return file_keys

    def _hash_components(self) -> tuple:
        return ("local", self.media_path)
