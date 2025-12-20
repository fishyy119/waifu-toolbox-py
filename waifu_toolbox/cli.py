import argparse
import random
from pathlib import Path

from .db.operations import (
    change_repo_path,
    create_repo,
    purge_repo,
    show_repo_info,
    update_repo,
)

random.seed(42)


def main():
    parser = argparse.ArgumentParser(description="Waifu Toolbox CLI")
    subparsers = parser.add_subparsers(title="subcommands", dest="command", required=True, help="Available subcommands")

    # ========================
    # repo 子命令（二级）
    # ========================
    repo_parser = subparsers.add_parser(
        "repo",
        help="Manage feature repositories",
    )
    repo_subparsers = repo_parser.add_subparsers(
        title="repo commands",
        dest="repo_command",
        required=True,
    )

    # -------- create --------
    repo_create = repo_subparsers.add_parser("create", help="Create a new repository from a labeled folder")
    repo_create.add_argument("-n", "--name", required=True, help="Repository name")
    repo_create.add_argument("-p", "--path", type=Path, required=True, help="Path to labeled image folder")

    # -------- update --------
    repo_update = repo_subparsers.add_parser("update", help="Update an existing repository")
    repo_update.add_argument("-n", "--name", required=True, help="Repository name")
    repo_update.add_argument(
        "--purge", action="store_true", help="Remove images from the repository index that no longer exist on disk"
    )
    repo_update.add_argument(
        "--set-path", type=Path, default=None, help="Set or change the root path of the repository"
    )

    # -------- info --------
    repo_info = repo_subparsers.add_parser("info", help="Show repository information")
    repo_info.add_argument("-n", "--name", required=True, help="Repository name")

    # ========================
    # classify 子命令
    # ========================
    classify_parser = subparsers.add_parser(
        "classify", help="Classify images based on labeled repository and CCIP clustering"
    )
    classify_parser.add_argument(
        "-r", "--repo", type=str, required=False, default=None, help="Name of the labeled repository"
    )
    classify_parser.add_argument(
        "-w", "--wait-classify", type=Path, required=True, help="Path to root folder of images to classify"
    )
    classify_parser.add_argument(
        "-n", "--num-references", type=int, default=20, help="Number of reference images to use per category"
    )
    classify_parser.add_argument(
        "--inplace", action="store_true", help="If just cluster, the report will be saved in the original folder"
    )

    # ========================
    # sort 子命令
    # ========================
    sort_parser = subparsers.add_parser(
        "sort", help="Sort images in directories based on perceptual similarity (LPIPS + MST-TSP)"
    )
    sort_parser.add_argument(
        "-d", "--dir", type=Path, required=True, help="Root directory containing images or subdirectories to sort"
    )
    sort_parser.add_argument(
        "-m", "--memory-limit", type=int, default=2048, help="Memory limit in MB (default 2048 for 200 images)"
    )

    args = parser.parse_args()

    if args.command == "classify":
        from .core.classification import classify_by_ccip, just_cluster_by_ccip

        if args.repo is None:
            just_cluster_by_ccip(args.wait_classify, args.inplace)
        else:
            classify_by_ccip(args.repo, args.wait_classify, args.num_references)

    elif args.command == "sort":
        from .core.sort import sort_images_by_perceptual_similarity

        sort_images_by_perceptual_similarity(args.dir, args.memory_limit)

    elif args.command == "repo":
        if args.repo_command == "create":
            create_repo(args.name, args.path)

        elif args.repo_command == "info":
            show_repo_info(args.name)

        elif args.repo_command == "update":
            if args.purge:
                purge_repo(args.name)
            elif args.set_path:
                change_repo_path(args.name, new_path=args.set_path)
            else:
                update_repo(args.name)


if __name__ == "__main__":
    main()
