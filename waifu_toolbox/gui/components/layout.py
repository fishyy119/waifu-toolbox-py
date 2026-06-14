from typing import TypedDict

from nicegui import ui


class Theme(TypedDict):
    primary: str
    foreground: str
    muted_foreground: str
    border: str


THEME: Theme = {
    "primary": "#18181b",
    "foreground": "#09090b",
    "muted_foreground": "#71717a",
    "border": "#e4e4e7",
}

SHADCN_CSS = """
:root {
    --background: #ffffff;
    --foreground: #09090b;
    --card: #ffffff;
    --card-foreground: #09090b;
    --primary: #18181b;
    --primary-foreground: #fafafa;
    --secondary: #f4f4f5;
    --secondary-foreground: #18181b;
    --muted: #f4f4f5;
    --muted-foreground: #71717a;
    --accent: #f4f4f5;
    --accent-foreground: #18181b;
    --destructive: #ef4444;
    --destructive-foreground: #fafafa;
    --border: #e4e4e7;
    --input: #e4e4e7;
    --ring: #18181b;
    --radius: 0.5rem;

    --success: #16a34a;
    --success-bg: #f0fdf4;
    --success-border: #bbf7d0;
    --warning: #a16207;
    --warning-bg: #fefce8;
    --warning-border: #fef08a;
    --destructive-bg: #fef2f2;
    --destructive-border: #fecaca;

    --q-primary: var(--primary);
    --q-positive: var(--success);
    --q-negative: var(--destructive);
    --q-warning: var(--warning);
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    color: var(--foreground);
    background: var(--background);
}
.q-card {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
}
.q-separator {
    background-color: var(--border) !important;
}
.q-badge {
    border-radius: 9999px;
    font-weight: 500;
}
.q-linear-progress {
    border-radius: 9999px;
}
.q-field--outlined .q-field__control {
    border-radius: calc(var(--radius) - 2px);
}

/* Shadcn semantic utilities */
.text-foreground { color: var(--foreground); }
.text-muted { color: var(--muted-foreground); }
.text-destructive-fg { color: var(--destructive); }
.text-success { color: var(--success); }
.bg-muted { background-color: var(--muted); }
.bg-accent { background-color: var(--accent); }
.border-default { border-color: var(--border); }

/* Badge variants */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 500;
    border-radius: 9999px;
    border: 1px solid var(--border);
    color: var(--muted-foreground);
}
.badge-success {
    background: var(--success-bg);
    border-color: var(--success-border);
    color: var(--success);
}
.badge-warning {
    background: var(--warning-bg);
    border-color: var(--warning-border);
    color: var(--warning);
}
.badge-destructive {
    background: var(--destructive-bg);
    border-color: var(--destructive-border);
    color: var(--destructive);
}

/* Navigation */
.nav-link {
    display: block;
    width: 100%;
    padding: 0.5rem 0.75rem;
    border-radius: calc(var(--radius) - 2px);
    color: var(--muted-foreground);
    text-decoration: none;
    font-size: 0.875rem;
    font-weight: 500;
    transition: background-color 0.15s, color 0.15s;
    box-sizing: border-box;
}
.nav-link:hover {
    background-color: var(--accent);
    color: var(--accent-foreground);
}
.nav-link-active {
    background-color: var(--accent);
    color: var(--foreground);
    font-weight: 600;
}
"""

IMAGE_VIEWER_CSS = """
.masonry-grid {
    display: grid;
    grid-auto-flow: row dense;
    grid-auto-rows: 8px;
    gap: 8px;
    align-items: start;
}
.masonry-grid .masonry-item {
    overflow: hidden;
    border-radius: 4px;
}
.masonry-grid .masonry-item img {
    width: 100%; display: block; cursor: zoom-in;
}
"""

_shared_assets_ready = False


_NAV_ITEMS = [
    ("仓库列表", "/"),
    ("分类", "/classify"),
    ("排序", "/sort"),
    ("格式转换", "/convert"),
    ("相似搜索", "/search"),
]

_NAV_SECONDARY = [
    ("任务队列", "/tasks"),
    ("设置", "/settings"),
]


def ensure_shared_assets() -> None:
    global _shared_assets_ready
    if _shared_assets_ready:
        return
    ui.add_css(SHADCN_CSS, shared=True)
    ui.add_css(IMAGE_VIEWER_CSS, shared=True)
    ui.add_head_html('<script src="/assets/image_viewer.js"></script>', shared=True)
    _shared_assets_ready = True


def page_layout(path: str):
    ensure_shared_assets()
    ui.dark_mode(False)

    with (
        ui.header()
        .classes("items-center")
        .style(
            "background: var(--background); color: var(--foreground);"
            "border-bottom: 1px solid var(--border); box-shadow: none;"
        )
    ):
        ui.button(icon="menu", on_click=lambda: left_drawer.toggle()).props("flat dense color=dark")
        ui.label("Waifu Toolbox").classes("text-base font-semibold tracking-tight px-3")

    left_drawer = ui.left_drawer(value=True).style(
        "background: var(--background); border-right: 1px solid var(--border);" "padding: 1rem 0.75rem;"
    )
    with left_drawer:
        with ui.column().classes("w-full gap-0.5 mt-3"):
            for label, href in _NAV_ITEMS:
                _nav_link(label, href, path)

            ui.separator().classes("my-2")

            for label, href in _NAV_SECONDARY:
                _nav_link(label, href, path)


def _nav_link(label: str, href: str, current_path: str):
    if href == "/":
        active = current_path == "/" or current_path.startswith("/repo")
    else:
        active = current_path.startswith(href)
    cls = "nav-link no-underline"
    if active:
        cls += " nav-link-active"
    ui.link(label, href).classes(cls)
