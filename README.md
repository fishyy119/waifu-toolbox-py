# waifu-toolbox-py

Python 3.12 (dghs-imgutils 0.19.0)

## Repo

repo 命令用于构建仓库索引，分类功能（仓库的一级子目录被视为图片的标签，忽略处于根目录的图片）基于已经构建好的仓库。其位于项目根目录下的 `database` 中，相关命令如下：

```shell
python cli.py repo create -n "仓库名" -p "仓库路径"  # 创建仓库

python cli.py repo update -n "仓库名"  # 更新索引
python cli.py repo update -n "仓库名" --purge  # 去除无效索引
python cli.py repo update -n "仓库名" --deduplicate  # 基于文件hash去重
python cli.py repo update -n "仓库名" --set-path "仓库路径"  # 修改仓库路径

python cli.py repo info -n "仓库名"  # 查询仓库信息

python cli.py repo flatten -n "仓库名"  # 将各分类的嵌套文件夹扁平化
```

> flatten 命令考虑场景为将图片导出到手机上时，由于大多数手机相册应用都不支持嵌套的相册查看，所以需要进行一步扁平化操作。
>
> 扁平化后，将在仓库同级处生成 `_{repo_name}_flat` 文件夹（在开始扁平化前其会被先**清空**），其中仅保留一级子目录，扁平化不涉及重命名操作

## Classify

classify 命令用于将待整理图片分类，基于`dghs-imgutils`提供的 CCIP 模型进行**角色级**的特征聚类。

```shell
# 参考分类好的仓库，分类待整理图片
python cli.py classify "待整理目录" -r "仓库名" -n 20

# 仅进行角色聚类，无参考
python cli.py classify "待整理目录"
python cli.py classify "待整理目录" --inplace  # 原地整理
```

> [!NOTE]
> 参数 `-n` 用于从仓库的每个分类中抽取一定数量的参考图片作为分类参考，其选取应当适中
>
> - 若该值过大，聚类运行时间会增加，同时大量的簇会集中在仓库内部无法构成参考
> - 若该值过小，则存在仓库中各种特征无法被充分采样到的可能
>
> 受限于聚类方法，可以对未分类成功得到图片集合多次分类，最终无法分类的图片会收敛

## Sort

sort 命令用于基于感知差异的图片排序，其会对每个包含图片的子目录单独进行排序。基于`dghs-imgutils`提供的 LPIPS 模型

```shell
python cli.py sort "目标目录"
python cli.py sort "目标目录" -m 1024  # 限制内存开销为1024MB
python cli.py sort "目标目录" --avoid-sorted  # 跳过已排序的文件夹
```

> [!NOTE]
> 该模型提取出的特征未经过压缩，占据内存空间极大（约100张/GB），因此在图片数量过多超出内存限制的情况下，需要将特征缓存到文件系统，这会很大程度上增加时间开销。
>
> 不启用缓存的图片最大允许张数 `N` 与内存限制值 `M` 之间的关系为：`N = (M / 1024) * 100`
>
> > 仅为数学计算，并非强制内存限制，实际内存开销可能会有一定出入
>

## Convert

convert 命令用于将压缩性能较低的格式(bmp)转换为webp格式。

```shell
python cli.py convert "目标目录" # 将目标目录下的 bmp 图片转换为 webp 格式
python cli.py convert "目标目录" -r # 替换原文件
```
