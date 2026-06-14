# pyright: reportUnusedFunction=false
from pathlib import Path

from nicegui import app, ui

from .pages import (
    classify,
    convert,
    dashboard,
    repo_detail,
    search,
    settings,
    sort,
    tasks,
)


def run(dev: bool = False):
    assets_dir = Path(__file__).with_name("assets")
    app.add_static_files("/assets", assets_dir)

    @ui.page("/")
    def index():
        dashboard.render()

    @ui.page("/repo/{repo_name}")
    def repo_page(repo_name: str):
        repo_detail.render(repo_name)

    @ui.page("/classify")
    def classify_page():
        classify.render()

    @ui.page("/sort")
    def sort_page():
        sort.render()

    @ui.page("/convert")
    def convert_page():
        convert.render()

    @ui.page("/search")
    def search_page():
        search.render()

    @ui.page("/tasks")
    def tasks_page():
        tasks.render()

    @ui.page("/settings")
    def settings_page():
        settings.render()

    ui.run(
        title="Waifu Toolbox",
        port=3039,
        reload=dev,
        favicon=assets_dir / "favicon.png",
        dark=False,
    )
