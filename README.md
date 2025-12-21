# waifu-toolbox-py

Python 3.12 (dghs-imgutils 0.19.0)

## repo

repo 命令用于构建仓库索引，分类功能（仓库的一级子目录被视为图片的标签，忽略处于根目录的图片）基于已经构建好的仓库。其位于项目根目录下的 `database` 中，相关命令如下：

```shell
python -m waifu_toolbox.cli repo create -n "仓库名" -p "仓库路径"  # 创建仓库

python -m waifu_toolbox.cli repo update -n "仓库名"  # 更新索引
python -m waifu_toolbox.cli repo update -n "仓库名" --purge  # 去除无效索引
python -m waifu_toolbox.cli repo update -n "仓库名" --set-path "仓库路径"  # 修改仓库路径

python -m waifu_toolbox.cli repo info -n "仓库名"  # 查询仓库信息
```

## Classify

classify 命令用于将待整理图片分类，基于`dghs-imgutils`提供的 CCIP 模型进行**角色级**的特征聚类。

```shell
# 参考分类好的仓库，分类待整理图片
python -m waifu_toolbox.cli classify -r "仓库名" -w "待整理目录" -n 20

# 仅进行角色聚类，无参考
python -m waifu_toolbox.cli classify -w "待整理目录"
python -m waifu_toolbox.cli classify -w "待整理目录" --inplace  # 原地整理
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
python -m waifu_toolbox.cli sort -d "目标目录"
python -m waifu_toolbox.cli sort -d "目标目录" -m 1024  # 限制内存开销为1024MB
python -m waifu_toolbox.cli sort -d "目标目录" --avoid-sorted  # 跳过已排序的文件夹
```

> [!NOTE]
> 该模型提取出的特征未经过压缩，占据内存空间极大（约100张/GB），因此在图片数量过多超出内存限制的情况下，需要将特征缓存到文件系统，这会很大程度上增加时间开销。
>
> 不启用缓存的图片最大允许张数 `N` 与内存限制值 `M` 之间的关系为：`N = (M / 1024) * 100`
>
> > 仅为数学计算，并非强制内存限制，实际内存开销可能会有一定出入
>
