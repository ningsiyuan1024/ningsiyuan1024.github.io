# Sylan 的个人博客

网站：https://ningsiyuan1024.github.io/

文章以已公开发表的作者版本为准。原文、强调和图片保留；平台脚本和追踪代码不进入博客。每篇包含原平台链接。正文在 `content/<slug>/body.html`，标题、发布日期和来源在同目录 `article.json`。

## 本地运行

需要 Python 3.11 或更新版本，无第三方依赖。

```sh
python build.py
python verify.py
python -m http.server 8769 --directory dist
```

## 同步已发表文章

从当前公开页面取得完整正文并核对作者和发表状态。准备一个 JSON，字段为 `slug`、`title`、`published_at`、`source_url`、`platform`、`html`、`status: "published_verified"`，可选 `cover_url`。只导入公开版本，不以本地草稿替代。撤回文章不得重新导入。

```sh
python import_article.py /absolute/path/to/verified-snapshot.json
python build.py
python verify.py
```

检查本地阅读效果后提交并推送到 `main`，GitHub Actions 会构建、校验并部署。完成后核对对应运行和公开页面。相同文章沿用 slug，可更新原页面；不要因改标题而重复建文。源稿撤回或删除需先确认处理博客副本的范围。

这里的自动化仅负责仓库更新后的构建与部署。文章采集由发布工作流执行，没有后台抓取平台草稿或自行生成文章的任务。
