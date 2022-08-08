import inspect
import typing as t
from enum import Enum

from piccolo.table import Table
from starlette.requests import Request


class HookType(Enum):
    """
    When the hook should be applied.
    """

    pre_save = "pre_save"
    pre_patch = "pre_patch"
    pre_delete = "pre_delete"


class Hook:
    def __init__(self, hook_type: HookType, callable: t.Callable) -> None:
        self.hook_type = hook_type
        self.callable = callable


async def execute_post_hooks(
    hooks: t.Dict[HookType, t.List[Hook]],
    hook_type: HookType,
    row: Table,
    request: Request,
):
    for hook in hooks.get(hook_type, []):
        signature = inspect.signature(hook.callable)
        kwargs: t.Dict[str, t.Any] = dict(row=row)
        # Include request in hook call arguments if possible
        if {i for i in signature.parameters.keys()}.intersection(
            {"kwargs", "request"}
        ):
            kwargs.update(request=request)
        if inspect.iscoroutinefunction(hook.callable):
            row = await hook.callable(**kwargs)
        else:
            row = hook.callable(**kwargs)
    return row


async def execute_patch_hooks(
    hooks: t.Dict[HookType, t.List[Hook]],
    hook_type: HookType,
    row_id: t.Any,
    values: t.Dict[t.Any, t.Any],
    request: Request,
) -> t.Dict[t.Any, t.Any]:
    for hook in hooks.get(hook_type, []):
        signature = inspect.signature(hook.callable)
        kwargs = dict(row_id=row_id, values=values)
        # Include request in hook call arguments if possible
        if {i for i in signature.parameters.keys()}.intersection(
            {"kwargs", "request"}
        ):
            kwargs.update(request=request)
        if inspect.iscoroutinefunction(hook.callable):
            values = await hook.callable(**kwargs)
        else:
            values = hook.callable(**kwargs)
    return values


async def execute_delete_hooks(
    hooks: t.Dict[HookType, t.List[Hook]],
    hook_type: HookType,
    row_id: t.Any,
    request: Request,
):
    for hook in hooks.get(hook_type, []):
        signature = inspect.signature(hook.callable)
        kwargs = dict(row_id=row_id)
        # Include request in hook call arguments if possible
        if {i for i in signature.parameters.keys()}.intersection(
            {"kwargs", "request"}
        ):
            kwargs.update(request=request)
        if inspect.iscoroutinefunction(hook.callable):
            await hook.callable(**kwargs)
        else:
            hook.callable(**kwargs)
