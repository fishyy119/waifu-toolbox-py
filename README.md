# waifu-toolbox-py

Python 3.12

```shell
conda install -c conda-forge cuda=12.5 cudnn
```

## Classify

classify 命令用于将待整理图片分类，基于`dghs-imgutils`提供的 CCIP 模型进行**角色级**的特征聚类。

```shell
# 参考分类好的仓库，分类待整理图片
python -m waifu_toolbox.cli classify -r "仓库名" -w "待整理目录" 

# 仅进行角色聚类，无参考
python -m waifu_toolbox.cli classify -w "待整理目录"
python -m waifu_toolbox.cli classify -w "待整理目录" --inplace  # 原地整理
```
