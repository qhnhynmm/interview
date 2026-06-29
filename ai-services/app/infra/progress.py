from collections.abc import Awaitable, Callable

ProgressFn = Callable[[str, str], Awaitable[None]]