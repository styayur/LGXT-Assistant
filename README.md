# LGXT Assistant（理工学堂助手）v3.0

理工学堂助手是一个面向理工学堂平台的桌面小工具：登录后查看课程与作业、
浏览题目、将作业题目（含图片与答案）导出为 Word / PDF，并支持批量提交成绩。

本版本在保留既有功能、业务逻辑、API 行为与交互流程的前提下，完成：

- 代码精简与模块化重构（UI / API / 任务 / 导出 / 配置 职责分离）；
- 稳定性优化：后台线程不再直接操作控件，统一经 queue + 主线程轮询更新 UI；
- 页面数据异步加载，避免网络请求阻塞界面；
- 导出图片缓存，重复导出不重复下载；
- Developer Tool / Dark / Technical 视觉风格。

## 运行

环境要求：Python 3.7+（Windows）。

```bash
pip install -r requirements.txt
python default.pyw
```

## 项目结构

| 文件 | 职责 |
|---|---|
| `default.pyw` | 启动入口 |
| `theme.py` | UI 设计令牌与主题应用 |
| `ui.py` | 主窗口 / 页面 / 异步加载 / 任务适配器 |
| `api.py` | API 客户端（session、鉴权、统一错误结构） |
| `tasks.py` | 题目收集 / 批量提交 / 批量导出（worker） |
| `exporter.py` | 图片缓存 + Word / PDF 导出 |
| `config.py` | config.ini 设置与本地凭据（keyring） |

线程约定：worker 只通过 ui 适配器（内部 queue）上报事件；所有控件更新发生在
主线程轮询中；导出开关在主线程读取为快照后传入 worker。

## 功能

- 登录：用户名 + 密码，支持记住密码（本地凭据库）。
- 课程 / 作业：查看当前课程与作业列表（含剩余次数、截止时间、章节、成绩）。
- 题目：查看题目图片与答案，可单个提交成绩（0-100）。
- 导出：将作业题目导出为 Word / PDF，可包含答案与题目图片。
- 批量：一键将全部课程（或当前课程）的作业成绩提交为 100 分；批量导出
  全部课程（或当前课程）的作业。

## 依赖

```txt
keyring
requests
ttkbootstrap
Pillow
python-docx
reportlab
```

## 许可

GPL-3.0-or-later，详见 LICENSE。本工具仅限学习交流使用，请勿转卖或用于商业用途。
