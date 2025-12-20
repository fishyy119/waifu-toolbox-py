# pyright: standard
import random
import shutil
import time
from pathlib import Path

from imgutils.metrics.ccip import ccip_clustering

from waifu_toolbox.utils.console import log_debug, log_info, log_warn
from waifu_toolbox.utils.image import load_images_from_folder

random.seed(42)


# 测试函数
def test_ccip(folder: Path):

    all_images, file_paths = load_images_from_folder(folder, max_samples=1000, max_sample_rate=0.1)
    if not all_images:
        log_warn("未找到任何图片")
        return

    start_time = time.perf_counter()
    mapping = ccip_clustering(all_images)  # pyright: ignore[reportArgumentType]
    elapsed = time.perf_counter() - start_time
    log_debug(f"CCIP 聚类耗时：{elapsed:.2f} 秒 ({len(all_images)} 张图片)")

    assert len(file_paths) == len(mapping), "file_paths 与 mapping 长度不一致"

    # 创建 report 根目录
    report_root = folder.parent / "report_ccip"
    report_root.mkdir(exist_ok=True)

    # 遍历所有图片
    for path, cluster_id in zip(file_paths, mapping):
        cluster_dir = report_root / f"{cluster_id}"
        cluster_dir.mkdir(exist_ok=True)
        shutil.copy2(path, cluster_dir / path.name)

    log_info(f"聚类结果已保存到 {report_root}")


if __name__ == "__main__":
    folder_path = Path(input("请输入测试文件夹路径: "))
    test_ccip(folder_path)

# * 结论：效果不错，尤其是大量图片情形下
