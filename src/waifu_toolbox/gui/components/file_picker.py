import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Literal, Sequence, overload

from nicegui import run, ui


@overload
def path_picker(label: str, value: str, mode: Literal["directory"]) -> ui.input: ...


@overload
def path_picker(label: str, value: str, mode: Literal["file"], filetypes: Sequence[tuple[str, str]]) -> ui.input: ...


def path_picker(
    label: str = "路径",
    value: str = "",
    mode: Literal["directory", "file"] = "directory",
    filetypes: Sequence[tuple[str, str]] = (),
) -> ui.input:
    """
    路径选择输入框 + 浏览按钮。

    Args:
        mode: "directory" 选择文件夹, "file" 选择文件。
        filetypes: 文件模式下的过滤器，如 [("图片", "*.png *.jpg *.webp")]。
    """
    placeholder = "输入或浏览文件夹路径" if mode == "directory" else "输入或浏览文件路径"
    with ui.row().classes("w-full items-end gap-1 no-wrap"):
        path_input = ui.input(label=label, value=value, placeholder=placeholder).classes("flex-grow")

        async def pick():
            initial = path_input.value
            if mode == "directory":
                result = await run.io_bound(_ask_directory, initial)
            else:
                result = await run.io_bound(_ask_file, initial, filetypes)
            if result:
                path_input.set_value(result)

        ui.button(icon="folder_open", on_click=pick).props("flat round")
    return path_input


def folder_picker(label: str = "文件夹路径", value: str = "") -> ui.input:
    return path_picker(label=label, value=value, mode="directory")


def file_picker(
    label: str = "文件路径",
    value: str = "",
    filetypes: Sequence[tuple[str, str]] = (),
) -> ui.input:
    return path_picker(label=label, value=value, mode="file", filetypes=filetypes)


def _ask_directory(initial: str = "") -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # pyright: ignore[reportUnknownMemberType]
    result = filedialog.askdirectory(parent=root, initialdir=initial or None)
    root.destroy()
    return result or ""


def _ask_file(initial: str = "", filetypes: Sequence[tuple[str, str]] = ()) -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # pyright: ignore[reportUnknownMemberType]
    initial_dir = ""
    if initial:
        p = Path(initial)
        initial_dir = str(p.parent if p.is_file() else p) if p.exists() else initial
    ft = list(filetypes) if filetypes else [("所有文件", "*.*")]
    result = filedialog.askopenfilename(parent=root, initialdir=initial_dir or None, filetypes=ft)
    root.destroy()
    return result or ""
