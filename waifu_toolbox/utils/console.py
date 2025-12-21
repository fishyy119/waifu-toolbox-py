from functools import partial
from typing import List, Literal, Tuple

Color = Literal["red", "green", "yellow", "blue", "magenta", "cyan", "white", "reset"]

COLOR_CODES: dict[Color, str] = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "reset": "\033[0m",
}


def cprint_fast(
    texts: List[Tuple[str, Color] | str],
    sep: str = " ",
    end: str = "\n",
    flush: bool = False,
) -> None:
    """快速格式化复杂彩色文字"""
    colored_texts = []
    for t in texts:
        match t:
            case (text, color):  # tuple 解包
                colored_texts.append(f"{COLOR_CODES.get(color, COLOR_CODES['reset'])}{text}{COLOR_CODES['reset']}")
            case str():
                colored_texts.append(t)
            case _:
                raise TypeError(f"Unsupported type: {type(t)}")

    print(sep.join(colored_texts), end=end, flush=flush)


def cprint(
    *args: object,
    color: Color = "reset",
    sep: str = " ",
    end: str = "\n",
    flush: bool = False,
) -> None:
    """彩色打印文本"""
    text = sep.join(str(arg) for arg in args)
    colored_text = f"{COLOR_CODES.get(color, COLOR_CODES['reset'])}{text}{COLOR_CODES['reset']}"
    print(colored_text, end=end, flush=flush)


log_info = partial(cprint, "[INFO]", color="green")
log_warn = partial(cprint, "[WARN]", color="yellow")
log_error = partial(cprint, "[ERROR]", color="red")
log_debug = partial(cprint, "[DEBUG]", color="blue")
