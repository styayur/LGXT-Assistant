# LGXT Assistant · 理工学堂助手

以作业为中心的理工学堂助手：从提交管理、图片转 LaTeX，到 AI 辅助解题与学习资料导出。

**Beta。** Windows 桌面、Windows 网页与 Android 独立版本、独立验证。

[English](README.md) · [发布](https://github.com/styayur/LGXT-Assistant/releases) · [使用说明](docs/user-guide.md) · [安全](SECURITY.md) · [验证记录](docs/VERIFICATION.md)

[![Verify](https://github.com/styayur/LGXT-Assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/styayur/LGXT-Assistant/actions/workflows/tests.yml)
[![AGPL-3.0-only](https://img.shields.io/badge/license-AGPL--3.0--only-blue)](LICENSE)

![Assignment workspace fixture](docs/screenshots/assignment-desktop-fixture.png)

更新后的 React 作业工作区，题目与模型回复为明确的合成夹具；浏览器截图，不是 Android 原生截图。

## 从当前作业开始

进入课程与作业后选择题目，在同一工作区查看原图、校正题面、编辑 LaTeX、整理解答并追问 AI。支持资料须手动勾选，来源名称和引用文字可见；模型解释与平台答案分开显示，不编造引用或页码。

- **作业操作：** 浏览课程、截止时间、平台实际返回的次数与参考答案，导出抽样题目。「一键满分」支持当前作业、当前课程、全部课程，先显示数量和目标分数，再确认一次；提供逐项结果，取消只停止后续请求。
- **图片转 LaTeX：** 使用已配置的视觉模型识别完整原图或按百分比裁剪的区域，核对文字与公式源码后再应用。以印刷数学为目标，不保证手写、图形或识别准确率。
- **围绕题目的 AI：**「使用 AI 分析此题」发送所选题图、校正题面、已有解答和勾选文字资料。可在当前题目中追问，把检查过的回复加入解答。可关闭图片使用纯文字分析。
- **文档：** Tiptap 富文本，行内/独立公式源码编辑、表格、代码、图片、标题、列表及撤销重做。本地保存并保留上一版。导出 Markdown、Word、PDF；Word/PDF 中公式保留为 **LaTeX 源码**，不是 Word 原生公式或已排版的 PDF 数学。
- **Android：** 独立 Flet 界面，改进作业状态、原图缩放、题面/解答笔记与显式 AI/识别操作。支持离线本地资料、备份恢复，以及兼容接口的纯文字或显式视觉请求，密钥仅存内存；不包含桌面富文本编辑器、裁剪工具或 Word/PDF 导出。

## 平台连接限制

**2026 年 10 月 24 日，无凭据检查确认官方 HTTP 有响应，但无法验证 HTTPS。** 默认阻止明文登录及认证请求，不自动降级，不关闭证书验证。如明确选择本次不安全兼容模式，账号密码、令牌和成绩传输可能被窃取或篡改；界面持续显示警告，不保存平台凭据。有经过验证的 HTTPS API 时，可通过 `LGXT_API_BASE` 配置。证据与规则见 [安全说明](SECURITY.md)。

题图仅允许配置的平台主机、公共网络地址及受支持的位图格式；拒绝外部主机、重定向、私有 IP、无效图片、超限响应和不安全数据 URL。因此部分合法外部图床也可能无法加载，须单独审核后再支持。

AI 仅在用户发起时发送，内容会离开本机。请在 AI 设置核实当前服务/模型支持图片后勾选视觉能力；不根据自定义模型名猜测支持情况，服务仍可能拒绝。软件不附带模型密钥或真实平台账号。

## 按渠道下载

以发布页实际附件为准，源码压缩包不是可运行安装包。此次 Windows Beta tag 为桌面 **4.1.0**、网页 **4.2.0-web**。只有对应渠道完成验证并公开发布后才可下载，草稿附件不等于公开发布。Android **3.3.0** 已有测试 APK 候选，但尚未公开发布。见 [渠道规则](docs/release-channels.md) 和 [交付证据](docs/VERIFICATION.md)。

| 渠道 | 升级版本 / 状态 | 安装方式 |
| --- | --- | --- |
| Windows 桌面 | [v4.1.0 Beta](https://github.com/styayur/LGXT-Assistant/releases/tag/v4.1.0) | Windows 10/11 x64，需 WebView2；运行 EXE，或完整解压便携 ZIP，保留 `_internal` |
| Windows 网页 | [v4.2.0-web Beta](https://github.com/styayur/LGXT-Assistant/releases/tag/v4.2.0-web) | Windows 10/11 x64；启动 Web EXE，保留控制台，用 Edge/Chrome 打开私有本机链接；无需 WebView2 |
| Android | [v3.2.1](https://github.com/styayur/LGXT-Assistant/releases/tag/v3.2.1) | 尚未发布 3.3.0 APK：Pillow 13 候选已能打包并通过 Android 15 x86_64 模拟器验收；持久签名与升级路径决定仍是发布门禁。历史 3.2.1 不包含此次连接安全修复 |

新 Windows 附件名包含平台、渠道与版本；请对照该发布的 `SHA256SUMS.txt` 校验。未声明提供 MSI 或可信签名。历史 tag 与附件保持原样；曾有 Android 附件附在网页发布中，历史 Android 渠道请使用上表链接。

## 本地资料与开发

Windows 文档、会话与设置位于 `%APPDATA%\LGXT-Assistant\desktop`。退出后备份 `%APPDATA%\LGXT-Assistant`，导出文件另行备份。AI 密钥存系统凭据库。Android 笔记存本地应用存储，密钥仅存内存，并清理历史明文密码。退出登录清除当前平台令牌。

推荐 Python 3.13、Node.js 22 或 Vite 支持的更新版本：

```powershell
py -3.13 -m pip install -r requirements.txt -r requirements-dev.txt
npm ci --prefix frontend
npm run build --prefix frontend
py -3.13 default.pyw        # WebView2 桌面
py -3.13 web_app.py         # 本机浏览器渠道
py -3.13 default.pyw --legacy
```

[架构](docs/architecture.md) · [编辑器选择与许可](docs/editor-decision.md) · [验证命令](CONTRIBUTING.md) · [更新记录](CHANGELOG.md)

应用源代码采用 [AGPL-3.0-only](LICENSE)，作者 StyAyur。[历史署名与第三方声明](NOTICE.md) 保留。漏洞请通过 [GitHub 私密安全报告](https://github.com/styayur/LGXT-Assistant/security/advisories/new) 提交；普通问题可使用 [Issues](https://github.com/styayur/LGXT-Assistant/issues)。

原生 Android 15 模拟器截图：[登录](docs/screenshots/android-native-login.png) · [fixture 软键盘](docs/screenshots/android-native-keyboard-fixture.png) · [fixture 笔记保存](docs/screenshots/android-native-saved-fixture.png)。这些结果不代表真实 ARM64 设备兼容性。

Android 准备状态：[指南与备份](docs/android-beta.md) · [证据与限制](docs/research/ANDROID_LIMITATIONS.md)。测试/调试签名及 fixture APK 不作为发行版分发。
