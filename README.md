# LGXT Assistant · 理工学堂助手

> 一个面向理工学堂平台的 Windows 桌面工具：登录后查看课程与作业、浏览题目、
> 将作业题目（含图片与答案）导出为 **Word / PDF**，并支持批量提交成绩。
>
> UI 为 Developer-Tool / Dark / Technical 风格，支持**搜索 / 筛选 / 排序**与自适应布局。

![Login](docs/screenshots/login_1280.png)
![Courses](docs/screenshots/courses_1280.png)
![Works + Inspector](docs/screenshots/works_sel_1280.png)
![Questions 3-pane](docs/screenshots/questions_1280.png)

---

## 功能一览

| 分类 | 功能 |
|---|---|
| 登录 | 用户名 / 密码；记住密码（本地凭据库 keyring） |
| 课程 | 课程列表、按名称/ID **搜索**、按名称/ID **排序**、OPEN 进入作业 |
| 作业 | 左列表 + 右 **Inspector**；**搜索**（作业名/章节/ID）、**筛选**（全部/可提交/已用完）、**排序**（截止时间/剩余次数/名称）；单击选中、双击打开 |
| 题目 | 三栏：题目列表｜题面+图片｜Inspector（答案/成绩）；**搜索/筛选/排序**；`‹ ›` 切换 |
| 成绩 | 单题提交 0–100；批量把当前课程/全部课程作业提交为 100 |
| 导出 | 单作业 / 当前课程 / 全部课程 → Word(.docx) / PDF(.pdf) + 题目图片（重复导出有本地缓存，不重复下载） |
| 配置 | 导出路径、格式、是否含答案；保存到 `config.ini` |

## 环境要求

- Windows
- Python 3.7+

## 快速开始

```bash
# 1) 安装依赖
pip install -r requirements.txt

# 2) 运行
python default.pyw
```

依赖：`keyring` `requests` `ttkbootstrap` `Pillow` `python-docx` `reportlab`

## 使用教程

### 1. 登录
启动后在 AUTH 面板输入理工学堂用户名/密码，勾选“记住密码”可写入本地凭据库。
登录成功右上角状态变为 `● CONNECTED`。

### 2. 浏览课程
侧栏 → **课程列表**。顶部命令条：

- `SEARCH` 输入课程名或 ID，实时过滤；
- `SORT` 选择 名称 A→Z / Z→A / ID；
- `REFRESH` 重新拉取；`EXPORT ALL` / `SUBMIT ALL 100` 为全课程批量操作。

点行内 `OPEN` 进入该课程的作业页。

### 3. 作业页（List + Inspector）
- 左侧列表单击选中，右侧 **INSPECTOR** 显示 ID / 章节 / 截止 / 成绩 / 尝试次数 / 状态；
- 双击行或点 Inspector 的 `OPEN ▸ 题目` 进入题目页；
- `EXPORT 题目` 只导出当前选中的作业；
- 顶部命令条可 `SEARCH`（作业名/章节/ID）、`FILTER`（全部/可提交/已用完）、`SORT`，
  以及 `EXPORT ALL` / `SUBMIT ALL 100` / `REFRESH`；
- 页头 `‹ 返回课程列表` 返回。

### 4. 题目页（三栏工作区）
- 左栏题目列表：可用顶部 `SEARCH`（题名/答案/ID）、`FILTER`（全部/有答案/无图片）、`SORT`（编号/名称）；
- 中栏显示当前题目名称、ID 与题面图片（异步加载并缓存）；
- 右栏 **INSPECTOR** 显示答案，输入 0–100 后点 `SUBMIT` 提交该作业成绩；
- 使用 `‹` / `›` 切换题目，页头 `‹ 返回作业列表` 返回。

### 5. 导出与批量操作
- 导出到**设置页**配置的路径，目录结构：
  `导出路径/作业/<课程名>(ID_x)/<作业名>(ID_y)/题目图片/…docx/…pdf`
- 批量操作会在页面底部出现**内嵌 Task Panel** 显示进度，完成后弹出结果汇总；
- 无需长时间等待：页面加载、图片下载、提交、导出都在后台线程执行，界面不冻结。

### 6. 设置
- `EXPORT`：选择 Word / PDF、是否含答案；
- `PATH`：浏览选择导出目录；
- 右侧 `SYSTEM` 显示 API 地址、版本、许可、登录状态（真实信息）；
- `SAVE` 写入 `config.ini`；`USER INFO` 查看账号信息。

## 项目结构

```
default.pyw   入口（python default.pyw）
theme.py      UI 设计令牌与主题
ui.py         主窗口/页面/搜索筛选排序/异步加载/任务面板
api.py        API 客户端（session/鉴权/统一错误）
tasks.py      题目收集/批量提交/批量导出（后台线程）
exporter.py   图片缓存 + Word/PDF 导出
config.py     config.ini 设置 + 本地凭据
docs/         截图等文档资源
```

### 线程模型（开发者须知）

后台 worker **从不直接操作控件**：只把事件放入 `queue.Queue`，
主线程通过 `after(60ms)` 轮询把状态/进度/图片/结果应用到 UI。
导出开关在启动任务前由主线程读取为只读快照（`ExportOptions`），
因此批量任务进行中界面始终可响应。

## 许可

GPL-3.0-or-later，详见 [LICENSE](LICENSE)。
本工具仅限学习交流使用，请勿转卖或用于商业用途。
Author: Styayur
