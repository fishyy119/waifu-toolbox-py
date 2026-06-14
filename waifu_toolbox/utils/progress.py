from typing import Callable, Protocol

from tqdm import tqdm


class ProgressReporter(Protocol):
    def update(self, n: int = 1) -> None: ...
    def set_postfix(self, text: str) -> None: ...
    def close(self) -> None: ...


ProgressFactory = Callable[[int, str], ProgressReporter]


class TqdmProgress:
    def __init__(self, total: int, desc: str):
        self._bar = tqdm(total=total, desc=desc)

    def update(self, n: int = 1) -> None:
        self._bar.update(n)

    def set_postfix(self, text: str) -> None:
        self._bar.set_postfix_str(text)

    def close(self) -> None:
        self._bar.close()


def tqdm_factory(total: int, desc: str) -> ProgressReporter:
    return TqdmProgress(total, desc)
