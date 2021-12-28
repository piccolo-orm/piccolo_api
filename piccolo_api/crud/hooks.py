from enum import Enum
import typing as t

from piccolo.table import Table


class HookType(Enum):
    pre_save = "pre_save"
    pre_patch = "pre_patch"
    pre_delete = "pre_delete"


class Hook:
    def __init__(self, hook_type: HookType, coro) -> None:
        self.hook_type = hook_type
        self.coro = coro


async def execute_post_hooks(
    hooks: t.List[Hook], hook_type: HookType, row: Table
):
    hooks_to_exec = [x for x in hooks if x.hook_type == hook_type]
    for hook in hooks_to_exec:
        row = await hook.coro(row)
    return row


async def execute_patch_hooks(
    hooks: t.List[Hook],
    hook_type: HookType,
    row_id: t.Any,
    values: t.Dict[t.Any, t.Any],
) -> t.Dict[t.Any, t.Any]:
    hooks_to_exec = [x for x in hooks if x.hook_type == hook_type]
    for hook in hooks_to_exec:
        values = await hook.coro(row_id=row_id, values=values)
    return values


async def execute_delete_hooks(
    hooks: t.List[Hook], hook_type: HookType, row_id: t.Any
):
    hooks_to_exec = [x for x in hooks if x.hook_type == hook_type]
    for hook in hooks_to_exec:
        await hook.coro(row_id=row_id)
