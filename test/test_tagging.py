# pyright: standard
import random
from collections import Counter
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Literal, Set, TypeAlias

from imgutils.tagging import get_camie_tags, get_deepgelbooru_tags, get_wd14_tags

from waifu_toolbox.utils.console import log_debug, log_info
from waifu_toolbox.utils.image import load_images_from_folder

random.seed(42)


Level: TypeAlias = Literal["A", "B", "C", "D"]


def rate_to_level(rate: float) -> Level:
    if rate >= 0.8:
        return "A"
    elif rate >= 0.50:
        return "B"
    elif rate >= 0.20:
        return "C"
    else:
        return "D"


# 测试函数
def test_folder(folder: Path, tagger: Callable):
    summary: Dict[Level, Set[str]] = {
        "A": set(),
        "B": set(),
        "C": set(),
        "D": set(),
    }

    # 遍历子目录
    for subdir in folder.iterdir():
        if subdir.is_dir():
            log_debug(f"=== 测试单元: {subdir.name} ===")
            all_images, _ = load_images_from_folder(subdir, max_samples=100)
            if not all_images:
                continue

            merged_tags = set()
            success_count = 0

            for img in all_images:
                tags: Dict[str, float] = tagger(img)
                if tags:
                    success_count += 1
                    max_key = max(tags.items(), key=lambda x: x[1])[0]
                    merged_tags.add(max_key)

            success_rate = success_count / len(all_images)
            summary[rate_to_level(success_rate)].add(subdir.name)

            log_info(f"成功 {success_count}/{len(all_images)}, {merged_tags}")

    log_debug("=== 测试总结 ===")
    for level, dirs in summary.items():
        log_info(f"等级 {level} (合计 {len(dirs)}): {dirs}")


if __name__ == "__main__":
    folder_path = Path(input("请输入测试文件夹路径: "))
    test_folder(folder_path, partial(get_camie_tags, fmt="character"))  # 800MB, 只有他认识几个
    # test_folder(folder_path, partial(get_camie_tags, model_name="refined", fmt="character"))  # 1.7G, 完全无输出？
    # test_folder(folder_path, partial(get_wd14_tags, fmt="character"))  # 467MB, 完全无法识别
    # test_folder(folder_path, partial(get_deepgelbooru_tags, fmt="character"))  # 645MB, 完全无法识别

# * 结论
# 几乎无可用模型，绝大多数模型训练集完全没有见过游戏角色
# 部分模型能够识别少量热门角色，但同样伴随较高的假阳性
