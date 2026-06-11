# waifu-toolbox-py

Python 3.12 (`dghs-imgutils 0.19.0`, `dreamsim 0.2.1`)

## Install

推荐使用 editable install：

```shell
pip install -e .
```

安装后会提供两个命令入口：

- `waifu`：推荐的简写命令
- `waifu-toolbox`：完整命令别名

> [!NOTE]
> 仓库索引和特征缓存统一存放到用户目录下的 `~/.waifu/database/waifu.db`（SQLite）
>
> DreamSim 权重：`~/.waifu/dreamsim_models/`

## Repo

repo 命令用于构建仓库索引，分类功能（仓库的一级子目录被视为图片的标签，忽略处于根目录的图片）基于已经构建好的仓库。相关命令如下：

```shell
# 创建仓库（默认只构建 hash 索引，可选提取特征）
waifu repo create -n "仓库名" -p "仓库路径"
waifu repo create -n "仓库名" -p "仓库路径" --ccip            # 同时提取 CCIP 特征
waifu repo create -n "仓库名" -p "仓库路径" --dreamsim        # 同时提取 DreamSim 特征
waifu repo create -n "仓库名" -p "仓库路径" --ccip --dreamsim # 同时提取两种特征

# 更新索引（同步新增图片与标签变更，可选提取/补全特征）
waifu repo update -n "仓库名" --ccip       # 同步索引并提取/补全 CCIP 特征
waifu repo update -n "仓库名" --dreamsim   # 同步索引并提取/补全 DreamSim 特征
waifu repo update -n "仓库名" --purge      # 去除无效索引
waifu repo update -n "仓库名" --deduplicate  # 基于文件 hash 去重
waifu repo update -n "仓库名" --set-path "仓库路径"  # 修改仓库路径
waifu repo update -n "仓库名" --rename "新名"       # 重命名仓库

waifu repo list                    # 列出所有仓库
waifu repo info -n "仓库名"        # 查询仓库详细信息

waifu repo flatten -n "仓库名"     # 将各分类的嵌套文件夹扁平化

waifu repo analyze -n "仓库名"          # 分析文件类型占比
waifu repo analyze -n "仓库名" -c       # 分析各分类的文件占比
waifu repo analyze -n "仓库名" -s count # 结果排序
waifu repo analyze -n "仓库名" -d "xxx/xxx"  # 分析指定子目录
```

> flatten 命令考虑场景为将图片导出到手机上时，由于大多数手机相册应用都不支持嵌套的相册查看，所以需要进行一步扁平化操作。
>
> 扁平化后，将在仓库同级处生成 `_{repo_name}_flat` 文件夹（在开始扁平化前其会被先**清空**），其中仅保留一级子目录，扁平化不涉及重命名操作

## Cache

cache 命令用于管理特征缓存（存放于 `feature_cache` 表，按图片 hash 索引，与仓库无关）。

```shell
waifu cache clear              # 清空全部特征缓存
waifu cache clear --ccip       # 仅清空 CCIP 特征缓存
waifu cache clear --dreamsim   # 仅清空 DreamSim 特征缓存
```

## Classify

classify 命令用于将待整理图片分类，基于`dghs-imgutils`提供的 CCIP 模型进行**角色级**的特征聚类。

```shell
# 参考分类好的仓库，分类待整理图片
waifu classify "待整理目录" -r "仓库名" -n 20

# 仅进行角色聚类，无参考
waifu classify "待整理目录"
waifu classify "待整理目录" --inplace  # 原地整理
```

> [!NOTE]
> 参数 `-n` 用于从仓库的每个分类中抽取一定数量的参考图片作为分类参考，其选取应当适中
>
> - 若该值过大，聚类运行时间会增加，同时大量的簇会集中在仓库内部无法构成参考
> - 若该值过小，则存在仓库中各种特征无法被充分采样到的可能
>
> 受限于聚类方法，可以对未分类成功得到图片集合多次分类，最终无法分类的图片会收敛

## Sort

sort 命令用于基于 DreamSim embedding 的感知差异对图片排序，其会对每个包含图片的子目录单独进行排序。

```shell
waifu sort "目标目录"
waifu sort "目标目录" --avoid-sorted  # 跳过已排序的文件夹
```

## Convert

convert 命令用于将图片转换为webp格式。

```shell
waifu convert "目标目录" # 将目标目录下的 bmp 图片转换为 webp 格式
waifu convert "目标目录" -f png # 转换 png 图片
waifu convert "目标目录" -r # 替换原文件
```
