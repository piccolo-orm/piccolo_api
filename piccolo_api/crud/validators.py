from __future__ import annotations
from dataclasses import dataclass, field
import inspect
import functools
import typing as t

from starlette.requests import Request
from starlette.exceptions import HTTPException

if t.TYPE_CHECKING:
    from .endpoints import PiccoloCRUD


ValidatorFunction = t.Callable[["PiccoloCRUD", Request], None]


@dataclass
class Validators:
    """
    These validators are run by the corresponding method on PiccoloCRUD. Raise
    a Starlette exception if there is a problem.
    """

    every: t.List[ValidatorFunction] = field(default_factory=list)
    get_single: t.List[ValidatorFunction] = field(default_factory=list)
    put_single: t.List[ValidatorFunction] = field(default_factory=list)
    patch_single: t.List[ValidatorFunction] = field(default_factory=list)
    delete_single: t.List[ValidatorFunction] = field(default_factory=list)
    post_single: t.List[ValidatorFunction] = field(default_factory=list)
    get_all: t.List[ValidatorFunction] = field(default_factory=list)
    delete_all: t.List[ValidatorFunction] = field(default_factory=list)
    get_references: t.List[ValidatorFunction] = field(default_factory=list)
    get_ids: t.List[ValidatorFunction] = field(default_factory=list)
    get_new: t.List[ValidatorFunction] = field(default_factory=list)
    get_schema: t.List[ValidatorFunction] = field(default_factory=list)
    get_count: t.List[ValidatorFunction] = field(default_factory=list)
    extra_context: t.Dict[str, t.Any] = field(default_factory=dict)


def apply_validators(function):
    """
    A decorator used to apply validators to the corresponding methods on
    PiccoloCRUD.
    """

    def run_validators(*args, **kwargs):
        piccolo_crud: PiccoloCRUD = args[0]
        validators = piccolo_crud.validators

        request = kwargs.get("request") or next(
            (i for i in args if isinstance(i, Request)), None
        )

        validator_functions = (
            getattr(validators, function.__name__) + validators.every
        )
        if validator_functions and request:
            for validator_function in validator_functions:
                try:
                    validator_function(
                        request=request,
                        piccolo_crud=piccolo_crud,
                        **validators.extra_context
                    )
                except HTTPException as exception:
                    raise exception
                except Exception:
                    raise HTTPException(
                        status_code=400, detail="Validation error"
                    )

    @functools.wraps(function)
    async def inner_coroutine_function(*args, **kwargs):
        run_validators(*args, **kwargs)
        return await function(*args, **kwargs)

    @functools.wraps(function)
    def inner_function(*args, **kwargs):
        run_validators(*args, **kwargs)
        return function(*args, **kwargs)

    if inspect.iscoroutinefunction(function):
        return inner_coroutine_function
    else:
        return inner_function
