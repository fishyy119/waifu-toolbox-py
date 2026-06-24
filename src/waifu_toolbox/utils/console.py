from rich import print


def log_info(*args: object, sep: str = " ", end: str = "\n", flush: bool = False):
    print("[green][INFO][/green]", *args, sep=sep, end=end, flush=flush)


def log_warn(*args: object, sep: str = " ", end: str = "\n", flush: bool = False):
    print("[yellow][WARN][/yellow]", *args, sep=sep, end=end, flush=flush)


def log_error(*args: object, sep: str = " ", end: str = "\n", flush: bool = False):
    print("[red][ERROR][/red]", *args, sep=sep, end=end, flush=flush)


def log_debug(*args: object, sep: str = " ", end: str = "\n", flush: bool = False):
    print("[blue][DEBUG][/blue]", *args, sep=sep, end=end, flush=flush)
