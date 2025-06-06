from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, Union

from piccolo.utils.sync import run_sync
from starlette.exceptions import HTTPException
from starlette.requests import Request

if TYPE_CHECKING:  # pragma: no cover
    from .endpoints import PiccoloCRUD


ValidatorFunction = Callable[["PiccoloCRUD", Request], Union[Coroutine, None]]


class Validators:
    """
    These validators are run by the corresponding method on
    :class:`PiccoloCRUD`.

    The validator function is given the ``PiccoloCRUD`` instance, and the
    Starlette ``Request`` instance, and should raise a Starlette
    ``HTTPException`` if there is a problem.

    Async functions are also supported. Here are some examples:

    .. code-block:: python

        def validator_1(piccolo_crud: PiccoloCRUD, request: Request):
            if not request.user.user.superuser:
                raise HTTPException(
                    status_code=403,
                    "Only a superuser can do this"
                )

        async def validator_2(piccolo_crud: PiccoloCRUD, request: Request):
            if not await my_check_user_function(request.user.user):
                raise HTTPException(
                    status_code=403,
                    "The user can't do this."
                )

    """

    def __init__(
        self,
        every: list[ValidatorFunction] = [],
        get_single: list[ValidatorFunction] = [],
        put_single: list[ValidatorFunction] = [],
        patch_single: list[ValidatorFunction] = [],
        delete_single: list[ValidatorFunction] = [],
        post_single: list[ValidatorFunction] = [],
        get_all: list[ValidatorFunction] = [],
        delete_all: list[ValidatorFunction] = [],
        get_references: list[ValidatorFunction] = [],
        get_ids: list[ValidatorFunction] = [],
        get_new: list[ValidatorFunction] = [],
        get_schema: list[ValidatorFunction] = [],
        get_count: list[ValidatorFunction] = [],
        extra_context: dict[str, Any] = {},
    ):
        self.every = every
        self.get_single = get_single
        self.put_single = put_single
        self.patch_single = patch_single
        self.delete_single = delete_single
        self.post_single = post_single
        self.get_all = get_all
        self.delete_all = delete_all
        self.get_references = get_references
        self.get_ids = get_ids
        self.get_new = get_new
        self.get_schema = get_schema
        self.get_count = get_count
        self.extra_context = extra_context


def apply_validators(function):
    """
    A decorator used to apply validators to the corresponding methods on
    :class:`PiccoloCRUD`.
    """

    async def run_validators(*args, **kwargs) -> None:
        piccolo_crud: PiccoloCRUD = args[0]
        validators = piccolo_crud.validators

        if validators is None:
            return

        request = kwargs.get("request") or next(
            (i for i in args if isinstance(i, Request)), None
        )

        validator_functions = (
            getattr(validators, function.__name__) + validators.every
        )
        if validator_functions and request:
            for validator_function in validator_functions:
                try:
                    if inspect.iscoroutinefunction(validator_function):
                        await validator_function(
                            request=request,
                            piccolo_crud=piccolo_crud,
                            **validators.extra_context,
                        )
                    else:
                        validator_function(
                            request=request,
                            piccolo_crud=piccolo_crud,
                            **validators.extra_context,
                        )
                except HTTPException as exception:
                    raise exception
                except Exception:
                    raise HTTPException(
                        status_code=400, detail="Validation error"
                    )

    if inspect.iscoroutinefunction(function):

        @functools.wraps(function)
        async def inner_coroutine_function(*args, **kwargs):
            await run_validators(*args, **kwargs)
            return await function(*args, **kwargs)

        return inner_coroutine_function

    else:

        @functools.wraps(function)
        def inner_function(*args, **kwargs):
            run_sync(run_validators(*args, **kwargs))
            return function(*args, **kwargs)

        return inner_function
