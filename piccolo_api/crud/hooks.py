from enum import Enum

class HookType(Enum):
    pre_save = "pre_save"

class Hook():
    def __init__(self, hook_type: HookType, coro) -> None:
        self.hook_type = hook_type
        self.coro = coro
