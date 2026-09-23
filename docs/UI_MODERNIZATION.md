# LGXT Assistant 桌面 UI / UX 重构

## 架构分析与选择

原桌面为 Tkinter / ttkbootstrap，多页面以 mixin 组合到 `ui.App`。`api.py` 管理平台登录态，`tasks.py` 负责收集、批量导出和提交，`exporter.py` 生成 Word / PDF，`config.py` 管理 INI 和系统凭据。Android 使用独立的 Flet 入口。

主要体验问题包括：隐藏原生窗口栏且 Esc 退出、1200×800 的最小尺寸、固定宽度的三栏、持续 20 FPS 星点重绘、切角与发光控件、缩放字体和容器尺寸的耦合、英文控制台式标签，以及列表重建与业务回调混合。原项目没有 AI 对话服务。

为实现稳定的富文本、数学公式、响应式布局与键盘交互，新桌面采用本地 React 页面 + pywebview / Windows WebView2。保留 Python 业务服务和 Tk 兼容入口，避免改变原平台请求、导出结构与 Android 功能。新界面使用完整独立页面，不在旧星图上叠加局部皮肤。

实施顺序：业务接口检查 → 设计变量与三栏布局 → 桌面桥接及独立存储 → 课程 / 聊天 / 设置组件 → 流式与文件上下文 → 回归、截图及打包。

## 设计方案

采用适合学习与长内容阅读的安静工作台：低饱和石墨灰、蓝色操作强调、内容左对齐，欢迎页居中。相较原有太空与控制台风格，减少视觉噪声，将重点留给课程内容、公式和问题。保留 LGXT 的教育身份，图标使用毕业帽、课程、文件和学习任务。

| Token | 深色默认 | 作用 |
|---|---|---|
| `--bg` | `#191a1d` | 内容工作区 |
| `--sidebar` | `#141518` | 主导航 |
| `--panel` | `#1c1d21` | 上下文与卡片 |
| `--text` | `#edeef1` | 正文 |
| `--accent` | `#9db8ee` | 交互与选择状态 |
| `--border` | `#303238` | 容器分隔 |

字体优先 Segoe UI Variable / Segoe UI，中文回退 Microsoft YaHei UI。正文 14–16 px，辅助文字至少 11 px，页面标题 24–36 px。常规按钮高度 34 px；卡片圆角 10–16 px；较大的弹窗与输入器采用更宽松的圆角。阴影只用于输入器、浮层与弹窗。

```text
┌───────────────────┬──────────────────────────────┬──────────────────┐
│ 品牌 / 工作空间    │ 面包屑 / 模型 / 搜索          │ 上下文           │
│ 新会话             ├──────────────────────────────┤ 当前任务         │
│ 学习助手 / 课程    │ 聊天、课程、文件或设置        │ 文件引用         │
│ 工作区 / 提示词库  │ 内容宽度限制，避免超长行      │ 模型参数         │
│ 会话搜索与历史     │                              │ 连接 / 工具状态  │
│ 命令 / 设置 / 用户 ├──────────────────────────────┤                  │
│                   │ 附件 / 输入器 / 停止或发送    │ 本地存储提示     │
└───────────────────┴──────────────────────────────┴──────────────────┘
```

两侧可折叠；窗口变窄时上下文优先收起，860 px 下导航改为覆盖式抽屉。4K 下扩大面板并保持正文合理宽度。动效以 140–220 ms 的状态过渡为主，支持系统 reduced-motion 和应用内减少动态效果。

## 代码分层

```text
desktop/
  app.py             原生窗口入口及资源定位
  bridge.py          前端业务边界；原业务适配；后台任务
  models.py          Claude / OpenAI 兼容协议、SSE 流与连接测试
  storage.py         原子 JSON 写入、会话索引、工作区和偏好
  diagnostics.py     隔离用户数据的 WebView2 启动检查
frontend/src/
  App.jsx            路由、当前会话与异步任务协调
  lib/bridge.js      桌面调用；独立浏览器预览的本地存储适配
  components/
    ui.jsx           按钮、弹窗、Toggle、Toast、Skeleton、状态徽标
    sidebar/         Workspace 导航与会话索引
    chat/            对话与懒加载 Markdown 渲染
    settings/        分类设置
    dialogs/         命令面板
    Context.jsx      模型、资料和任务状态
    Courses.jsx      课程 → 作业 → 题目
    Workspace.jsx    文件工作区与提示词库
  styles/
    theme.css        深浅主题与设计变量
    app.css          布局、组件与响应式规则
```

异步桥接请求不会在 Tk / 浏览器 UI 线程执行网络工作。后台生成以增量偏移轮询；并发任务被互斥保护，旧课程请求的结果以请求序号丢弃。消息每 2.5 秒和结束时保存；会话索引不含消息正文，选中会话时才加载对应文件。持久化写入串行排队，避免旧结果覆盖新结果。

## 已实现的交互

- 深色、浅色、跟随系统；启动页偏好；减少动态效果。
- 左右栏折叠，原生 Windows 最小化、最大化、关闭及 F11 全屏。
- 会话新建、重命名、删除、标题搜索、草稿切换、Markdown 导出。
- 用户消息编辑与重新生成；替换后续内容前提供说明；流式停止保留已生成文本。
- Markdown、GFM 表格、代码高亮、KaTeX 数学、图片与附件卡片。消息内容不执行 HTML。
- Ctrl+K、Ctrl+Shift+P、Ctrl+N、Ctrl+Enter、Esc；命令列表支持键盘上下选择和执行。
- 模型服务配置、按 Provider 记忆 Endpoint / 模型 ID、凭据库存储密钥、真实连接测试。保存过的服务可由命令面板直接切换。
- 用户维护的长期学习指令、会话存储开关、持久化工作区资料与任务、可增删改的提示词模板。
- 课程搜索、作业筛选 / 排序、学习概览、题目图片 / 答案、将题目引用到 AI、单次和批量成绩提交、原 Word / PDF 导出。
- 加载骨架、任务进度、禁用状态、成功 / 错误通知、会话日志。无凭据时不伪造在线状态或回复。

## 性能与边界

- 初始 JS 约 270 KB（gzip 约 85 KB）；Markdown / 数学 / 高亮独立懒加载约 611 KB（gzip 约 184 KB）。设置、课程、工作区也独立分块。运行资源与字体全部本地打包。
- 消息初始渲染最近 40 条，向前按 40 条加载，并利用浏览器 `content-visibility` 跳过不可见内容；这是分页和浏览器渲染裁剪，不是固定行高虚拟列表。课程、作业、题目每页 20 项；会话索引按 40 条增量展示。
- 保存过的会话缓存最多保留约 12 个；日志保留 100 项；已完成后台 job 在下一个任务前清理。未开启会话保存时，当前窗口的临时会话会保留到退出。
- 文件支持 UTF-8 文本、代码、PNG / JPEG / WebP。每次最多 8 个、单文件 2 MB；文本读取最多 60,000 字符；工作区最多 80 个文件 / 32 MB。文件随消息显式提交，图片需要所选模型支持视觉。
- 长期记忆是手动维护的指令，不是自动学习；知识资料是文件引用，不包含向量数据库 / RAG。工具面板显示文件引用和真实导出任务，不代表模型可以自动执行任意工具。
- 英文覆盖主导航和主要聊天文案；课程业务与设置仍主要为中文。Android 无此次 UI 变更。
- 未配置真实模型密钥、未使用真实理工学堂账号执行网络操作。浏览器回归中的课程和回复为明确的测试夹具；真实服务连通性需要配置后在应用里测试。

## 验证与截图

```powershell
cd frontend
npm ci
npm run build
cd ..
py -3.13 -m pytest
py -3.13 scripts/check_frontend.py
py -3.13 scripts/check_native.py
```

Python 测试覆盖旧 API、导出、任务和 Tk 启动，新增会话持久化 / 删除、并发写入、路径限制、损坏数据保护、Provider 参数、中文 SSE、停止后保留输出、认证与成绩校验。前端测试检查主题持久化、命令与 Esc、模板创建、文件引用、公式 / 表格 / 高亮、消息编辑、流式停止与重试、课程分页和成绩确认。

首次截图检查发现 860 px 以下主工作区因覆盖式抽屉退出 Grid 布局而宽度归零，已通过显式设置 `main` 的 Grid 列修复，并加入主工作区最小可视宽度断言。避免只验证页面没有横向滚动而漏掉空白界面。

| 截图 | 内容 |
|---|---|
| [深色 1440×900](screenshots/modern-dark-1440.png) | 未配置模型的真实初始状态 |
| [深色 1280×720](screenshots/modern-dark-1280.png) | 紧凑桌面布局 |
| [深色 1920×1080](screenshots/modern-dark-1920.png) | 全高清布局 |
| [深色 3840×2160](screenshots/modern-dark-3840.png) | 4K 布局 |
| [860×600](screenshots/modern-dark-860.png) | 折叠侧栏的小窗口 |
| [浅色 1440×900](screenshots/modern-light-1440.png) | 浅色对话初始状态 |
| [浅色设置](screenshots/modern-settings-light.png) | 主题卡片与 Toggle |
| [对话渲染测试](screenshots/modern-chat-fixture.png) | 公式、表格、代码；内容为测试夹具 |
| [课程测试](screenshots/modern-courses-fixture.png) | 课程列表；账号和数据为测试夹具 |

Windows 打包脚本已先构建前端，再将前端 dist 和 pywebview 资源纳入 PyInstaller。支持单文件和便携目录，构建失败立即报错。可执行文件可使用 `--smoke-test <报告路径>` 在隐藏窗口中检查资源与桥接，不读取用户账号或写入用户配置。

参考实现协议：[pywebview API](https://pywebview.flowrl.com/api/)、[Claude Streaming Messages](https://platform.claude.com/docs/en/build-with-claude/streaming)、[Gemini OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai)。
