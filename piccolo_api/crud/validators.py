from __future__ import annotations

import functools
import inspect
import typing as t

from piccolo.utils.sync import run_sync
from starlette.exceptions import HTTPException
from starlette.requests import Request

if t.TYPE_CHECKING:  # pragma: no cover
    from .endpoints import PiccoloCRUD


ValidatorFunction = t.Callable[
    ["PiccoloCRUD", Request], t.Union[t.Coroutine, None]
]


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
        every: t.List[ValidatorFunction] = [],
        get_single: t.List[ValidatorFunction] = [],
        put_single: t.List[ValidatorFunction] = [],
        patch_single: t.List[ValidatorFunction] = [],
        delete_single: t.List[ValidatorFunction] = [],
        post_single: t.List[ValidatorFunction] = [],
        get_all: t.List[ValidatorFunction] = [],
        delete_all: t.List[ValidatorFunction] = [],
        get_references: t.List[ValidatorFunction] = [],
        get_ids: t.List[ValidatorFunction] = [],
        get_new: t.List[ValidatorFunction] = [],
        get_schema: t.List[ValidatorFunction] = [],
        get_count: t.List[ValidatorFunction] = [],
        extra_context: t.Dict[str, t.Any] = {},
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
