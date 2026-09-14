# LGXT Assistant v3.1.0 — 宇宙星链

## 本次更新

### UI / UX
- 无边框工作台：隐藏系统标题栏与最小化/关闭按钮；标题栏拖动、右下角三角缩放、ESC 退出（代码雨特效）
- 代码绘制的星空背景：星点漂浮闪烁；鼠标悬停产生向光标汇聚的青色光轨
- 课程星图：科目 = 恒星系，习题 = 行星；单击恒星展开/收起（懒加载），单击行星进入题目
- 金属切角面板与深色透光按钮：悬停光效 + 轻音效（设置页可关闭）
- 新增仪表盘：待激活 / 已完成 / 平均分（真实 API 数据）
- 帮助内容完善：窗口与快捷键、星图、仪表盘、导出、常见问题、声明

### 稳定性
- 登录不再被 keyring 异常打断；配置文件迁移到 %APPDATA%\\LGXT-Assistant
- 图片字节与 PhotoImage 缓存上限；字体对象池化；修复字体遮挡/裁切（容器、行高、列宽随缩放同步）
- 星图展开失败可重试；非数字题目 ID 排序不再崩溃
- 收集提前结束时取消未执行请求；页面在途请求上限 4
- API 错误分类（网络 / 非 JSON / 缺字段）与图片校验

### 工程
- ui 拆分为 ui/ 包（base / widgets / space / dashboard / 页面 mixin）
- pytest 测试集 23 项；README 全面重写为使用与开发指南

## 下载与安装（无需 Python 环境）

| 资产 | 适用场景 |
|---|---|
| `LGXT-Assistant.exe` | 单文件版：下载后双击即可运行 |
| `LGXT-Assistant-portable.zip` | 便携版：解压后运行 `LGXT-Assistant-portable.exe`，启动更快 |
| `LGXT-Assistant-3.1.0-setup.msi` | MSI 安装包：用户级安装（无需管理员），自动创建开始菜单快捷方式，可在「设置 → 应用」卸载 |
| `LGXT-Assistant-3.1.0-android.apk` | **Android 版**：Flet 实现，支持登录 / 仪表盘 / 课程-作业-题目浏览 / 成绩提交；侧载安装 |
| `LGXT-Assistant-SelfSigned.cer` | 自签名公钥证书（可选，用于本机验证签名） |
| `SHA256SUMS.txt` | 全部文件的 SHA-256 校验值（下载后建议校验） |

Windows 产物由 PyInstaller 打包，内置 Python 运行时与全部依赖（ttkbootstrap 主题、
Pillow、python-docx、reportlab、keyring 等），**在未安装 Python 的 Windows 电脑上可直接运行**
（已在剥离 Python 环境变量的条件下实测）。Android APK 由 Flet + GitHub Actions 云端构建，
内置三套 ABI，支持 Android 7.0+，可直接侧载安装。

源码运行：
```bash
pip install -r requirements.txt
python default.pyw
```

## 使用说明（每个文件的用法）

完整的下载 / 安装 / 卸载 / 校验步骤见 README「二、Release 文件使用方法（全部资产）」，摘要如下：

| 文件 | 使用方法 |
|---|---|
| `LGXT-Assistant.exe` | 下载后双击运行；SmartScreen 提示时点「更多信息 → 仍要运行」；删除文件即卸载 |
| `LGXT-Assistant-portable.zip` | 解压到普通目录（勿在压缩包内运行）→ 双击 `LGXT-Assistant-portable.exe`；删除文件夹即卸载 |
| `LGXT-Assistant-3.1.0-setup.msi` | 双击安装（用户级，无需管理员），开始菜单启动；`msiexec /x LGXT-Assistant-3.1.0-setup.msi` 卸载 |
| `LGXT-Assistant-3.1.0-android.apk` | 手机允许「安装未知应用」后点击安装；提示「应用未安装」时先卸载旧版并清理空间 |
| `LGXT-Assistant-SelfSigned.cer` | 可选：导入当前用户「受信任的根证书颁发机构」后，签名状态显示 Valid（仅测试用） |
| `SHA256SUMS.txt` | 与下载文件放同目录，用 `Get-FileHash -Algorithm SHA256` 或 `certutil -hashfile <文件> SHA256` 比对 |

签名验证：

```powershell
Get-AuthenticodeSignature .\LGXT-Assistant.exe | Format-List Status,SignerCertificate
# 未导入自签名证书时 Status = UnknownError（签名有效但根证书不受信任，属预期）
```

## 快捷操作
- `ESC` 退出（代码雨）
- `F11` 全屏 / 还原
- 单击恒星展开科目 → 单击行星打开题目

## 许可
GPL-3.0-or-later · 仅限学习交流使用，请勿转卖或用于商业用途 · Author: Styayur
