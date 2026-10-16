# 东华环院课程攻略（DHU-Env）

东华大学环境科学与工程学院课程攻略共享平台，仿照浙江大学能源工程学院开源项目 [ZJUSUEE.github.io](https://github.com/ZJUSUEE/ZJUSUEE.github.io)（源梦紫金）搭建，使用 **MkDocs + Material 主题**，可一键部署到 **GitHub Pages**。

## 项目内容

- **公共基础课程**：两个及以上专业共同修读的基础学科课程（数理、化学、力学、机械制图、电学），按学科模块组织；
- **公共专业课程**：两个及以上专业共同修读的专业课（流体力学、工程热力学、传热学、化工原理、环境监测等）；
- **六个专业方向**：
  - 能源与环境系统工程
  - 环境工程（卓越班）
  - 环境工程（环境工程与工商管理双学位）
  - 环境科学
  - 建筑环境与能源应用工程
  - 土木工程（绿色建造）

课程清单与学分、学时、建议学期等基本信息来源于 6 份教学计划总揽（2023a/2024a）。**所有课程页面的课程大纲、教材、资源、笔记、学习建议等均为「该部分待完善」状态**，需要后续由同学投稿与维护者填充——具体方法见 [docs/完善指南.md](docs/完善指南.md)。

## 快速开始

```bash
pip install mkdocs-material
mkdocs serve          # 本地预览 http://127.0.0.1:8000
mkdocs build          # 构建静态站点到 site/
```

## 部署到 GitHub Pages

1. 新建 GitHub 仓库（Public），推送本项目全部文件（含 `.github/workflows/ci.yml`）；
2. 仓库 **Settings → Pages** 将 Source 设为 **GitHub Actions**；
3. 每次 `git push` 自动构建发布，访问 `https://<用户名>.github.io/<仓库名>/`；
4. 修改 `mkdocs.yml` 顶部 `site_url` 为实际网址。

## 目录结构

```
docs/
├── index.md              首页
├── guideline.md          平台贡献指南（投稿规则）
├── 完善指南.md            站点完善指南（如何补齐各「待完善」部分）
├── courses.md            本科课程大纲（总导航）
└── courses/
    ├── public/           公共基础课程 + 公共专业课程
    └── routes/           六个专业方向
tools/                    站点生成工具链（可选，用于按培养方案重建全部课程页）
site/                     本地构建产物（可整体上传到任意静态托管）
```

## 说明

- 站点 Logo 使用东华大学环境科学与工程学院院徽（`docs/images/logo.jpg`）；
- 按建站要求，课程详情页不包含分数比例/考核方式部分；
- 维护与投稿联系方式为占位状态，请在 `docs/guideline.md` 中更新为实际邮箱；
- `tools/_generate_site.py` 可从教学计划批量重建全部课程页（会覆盖手动修改，运行前请备份）；日常维护建议直接编辑 `docs/` 下的 Markdown 文件。
