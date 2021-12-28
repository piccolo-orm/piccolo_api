import inspect
import typing as t
from enum import Enum

from piccolo.table import Table


class HookType(Enum):
    pre_save = "pre_save"
    pre_patch = "pre_patch"
    pre_delete = "pre_delete"


class Hook:
    def __init__(self, hook_type: HookType, callable: t.Callable) -> None:
        self.hook_type = hook_type
        self.callable = callable


async def execute_post_hooks(
    hooks: t.Dict[HookType, t.List[Hook]], hook_type: HookType, row: Table
):
    for hook in hooks.get(hook_type, []):
        if inspect.iscoroutinefunction(hook.callable):
            row = await hook.callable(row)
        else:
            row = hook.callable(row)
    return row


async def execute_patch_hooks(
    hooks: t.Dict[HookType, t.List[Hook]],
    hook_type: HookType,
    row_id: t.Any,
    values: t.Dict[t.Any, t.Any],
) -> t.Dict[t.Any, t.Any]:
    for hook in hooks.get(hook_type, []):
        if inspect.iscoroutinefunction(hook.callable):
            values = await hook.callable(row_id=row_id, values=values)
        else:
            values = hook.callable(row_id=row_id, values=values)
    return values


async def execute_delete_hooks(
    hooks: t.Dict[HookType, t.List[Hook]], hook_type: HookType, row_id: t.Any
):
    for hook in hooks.get(hook_type, []):
        if inspect.iscoroutinefunction(hook.callable):
            await hook.callable(row_id=row_id)
        else:
            hook.callable(row_id=row_id)
