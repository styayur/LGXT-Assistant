# LGXT Assistant · 理工学堂助手 v3.2.0（主推 Android 移动版）

> 面向理工学堂平台的工具：查看课程与作业、浏览题目、导出题目（桌面端 Word/PDF）、
> 提交成绩；桌面端为宇宙星链风 Developer Workbench，移动端为 Flet/Flutter 原生应用。
>
> **Android 版（推荐）**：手机直接安装 `LGXT-Assistant-3.2.0-android.apk`，无需 Python。

## ⬇️ 下载（Android 优先）

| 平台 | 文件 | 下载 |
|---|---|---|
| **Android（推荐）** | `LGXT-Assistant-3.2.0-android.apk` | [点击下载](https://github.com/styayur/LGXT-Assistant-3.0/releases/download/v3.2.0/LGXT-Assistant-3.2.0-android.apk) |
| Windows 安装版 | `LGXT-Assistant-3.2.0-setup.msi` | [点击下载](https://github.com/styayur/LGXT-Assistant-3.0/releases/download/v3.2.0/LGXT-Assistant-3.2.0-setup.msi) |
| Windows 单文件 | `LGXT-Assistant.exe` | [点击下载](https://github.com/styayur/LGXT-Assistant-3.0/releases/download/v3.2.0/LGXT-Assistant.exe) |
| Windows 便携版 | `LGXT-Assistant-portable.zip` | [点击下载](https://github.com/styayur/LGXT-Assistant-3.0/releases/download/v3.2.0/LGXT-Assistant-portable.zip) |
| 校验值 | `SHA256SUMS.txt` | [点击下载](https://github.com/styayur/LGXT-Assistant-3.0/releases/download/v3.2.0/SHA256SUMS.txt) |

Release 页面：<https://github.com/styayur/LGXT-Assistant-3.0/releases/tag/v3.2.0>

**Android 三步装机**：下载 APK → 允许「安装未知应用」→ 点击安装（Android 7.0+，支持 arm64-v8a / armeabi-v7a / x86_64）。

> Android 界面：**SafeArea 顶栏**（自动避让状态栏/刘海）+ 底部导航（仪表盘 / 课程 / 设置）；
> 手机返回键返回上一级菜单，根菜单连按两次返回退出。

![Star Map](docs/screenshots/starmap_1280.png)
![Dashboard](docs/screenshots/dashboard_1280.png)
![Questions](docs/screenshots/questions_1280.png)
![Matrix Rain](docs/screenshots/matrix_rain_1280.png)

---

## 一、快速开始

### Android（推荐）
1. 下载 `LGXT-Assistant-3.2.0-android.apk`；
2. 手机 设置 → 应用 → 特殊应用权限 → 安装未知应用 → 允许浏览器/文件管理器；
3. 点击 APK 安装并打开；登录后即可查看课程、作业、题目并提交成绩。

### Windows
- **安装版（推荐）**：双击 `LGXT-Assistant-3.2.0-setup.msi`，用户级安装、无需管理员，开始菜单启动；
- 单文件版：双击 `LGXT-Assistant.exe`（首次启动稍慢）；
- 便携版：解压 `LGXT-Assistant-portable.zip` 后运行 `LGXT-Assistant-portable.exe`。

### 从源码运行
```bash
pip install -r requirements.txt
python default.pyw            # Windows 桌面版
# Android/桌面跨平台移动版：
pip install flet==0.25.2
cd mobile && flet run         # 本地预览（手机端可用 flet run --android）
```

## 二、Release 文件使用方法（全部资产）

统一下载链接规则：`https://github.com/styayur/LGXT-Assistant-3.0/releases/download/v3.2.0/<文件名>`

| 资产 | 平台 | 用途 |
|---|---|---|
| `LGXT-Assistant-3.2.0-android.apk` | Android | **手机版（主推）**：侧载安装，Android 7.0+ |
| `LGXT-Assistant-3.2.0-setup.msi` | Windows | 安装包：用户级安装、开始菜单快捷方式、可卸载 |
| `LGXT-Assistant.exe` | Windows | 单文件版：下载双击即用（无需 Python） |
| `LGXT-Assistant-portable.zip` | Windows | 便携版：解压即用，启动更快，可放 U 盘 |
| `LGXT-Assistant-SelfSigned.cer` | Windows | 自签名公钥证书（可选，用于本机验证签名） |
| `SHA256SUMS.txt` | 通用 | 所有文件的 SHA-256 校验值 |

### 1. `LGXT-Assistant-3.2.0-android.apk`（Android 手机版，推荐）
1. 用手机浏览器打开 Release 下载 APK（或从电脑传输到手机）；
2. 允许「安装未知应用」：设置 → 应用 → 特殊应用权限 → 安装未知应用 → 允许浏览器/文件管理器；
3. 点击 APK 安装；若提示「应用未安装」：先卸载旧版本、确认剩余空间 ≥ 200MB、关闭安全中心的拦截提示后重试；
4. 支持 ABI：`arm64-v8a` / `armeabi-v7a` / `x86_64`；系统要求 Android 7.0+；
5. 功能：登录、仪表盘（待激活/已完成/平均分）、课程→作业→题目浏览、图片查看、成绩提交、设置；
   **移动端 v3.2 不含 Word/PDF 导出**（请在桌面版导出）；
6. 返回键行为：**返回上一级菜单**；已在根菜单（仪表盘/课程/设置）时连按两次返回才退出；
7. 卸载：长按图标 → 卸载（应用数据一并清除）。

### 2. `LGXT-Assistant-3.2.0-setup.msi`（Windows 安装包）
图形安装：双击 → 按提示完成（**用户级，无需管理员**）→ 从开始菜单启动。

```powershell
# 静默安装 / 卸载
msiexec /i LGXT-Assistant-3.2.0-setup.msi /qn /norestart
msiexec /x LGXT-Assistant-3.2.0-setup.msi /qn /norestart
```
- 安装位置：`%LOCALAPPDATA%\Programs\LGXT Assistant`
- 卸载也可在「设置 → 应用 → 已安装的应用」中完成

### 3. `LGXT-Assistant.exe`（Windows 单文件版）
1. 放到任意目录双击运行；2. SmartScreen 提示时点「更多信息 → 仍要运行」；
3. 配置：`%APPDATA%\LGXT-Assistant\config.ini`；凭据写入 Windows 凭据管理器；4. 删除文件即卸载。

### 4. `LGXT-Assistant-portable.zip`（Windows 便携版）
1. 解压到非系统保护目录（勿在压缩包内直接运行）；2. 双击 `LGXT-Assistant-portable.exe`；
3. 整个文件夹可整体拷贝/移动；4. 删除文件夹即卸载。

### 5. `LGXT-Assistant-SelfSigned.cer`（代码签名公钥，可选）
```powershell
Get-PfxCertificate .\LGXT-Assistant-SelfSigned.cer | Format-List Subject,Thumbprint,NotAfter
Import-Certificate -FilePath .\LGXT-Assistant-SelfSigned.cer -CertStoreLocation Cert:\CurrentUser\Root
Get-AuthenticodeSignature .\LGXT-Assistant.exe | Format-List Status,SignerCertificate
# 未导入证书时 Status = UnknownError（签名有效但根证书不受信任，属预期）
```
> 仅用于测试；生产环境请使用 CA 签发的代码签名证书（见第十三节）。

### 6. `SHA256SUMS.txt`（完整性校验，推荐）
```powershell
Get-FileHash .\LGXT-Assistant-3.2.0-android.apk -Algorithm SHA256
certutil -hashfile LGXT-Assistant.exe SHA256
```

本版本校验值（与 `SHA256SUMS.txt` 一致）：

| 文件 | 大小 (B) | SHA-256 |
|---|---|---|
| `LGXT-Assistant-3.2.0-android.apk` | 66,882,192 | `dfd711c7f3938cf22129a1a75f5cbdf4568522568f763c1d555070344b4c4a2b` |
| `LGXT-Assistant.exe` | 40,496,216 | `3941ea111984318eac6c666e2066b867a0c3d945b305f414979b3798a4e62bde` |
| `LGXT-Assistant-portable.zip` | 40,575,608 | `eea6abde380886603f640df38268aeedc8be2b2da65dd2988d05a73c3323625f` |
| `LGXT-Assistant-3.2.0-setup.msi` | 40,632,320 | `075ce80b7625d0a820f515b00d46387c7bc304d2096efb74509bf558a3015775` |
| `LGXT-Assistant-SelfSigned.cer` | 836 | `cdea811ab5b8b846e838fa25550efe948bee7ac7e98701060a5b7528d74bcd2f` |

### 7. 常见拦截与处理
| 现象 | 原因 | 处理 |
|---|---|---|
| Windows 提示「未知发布者」 | 自签名证书（未购买 CA 证书） | 点「更多信息 → 仍要运行」，或用自有证书重新签名（第十三节） |
| 手机提示「禁止安装」 | Android 默认禁止未知来源 | 允许浏览器/文件管理器安装未知应用 |
| 手机提示「应用未安装」 | 旧版本包名冲突/空间不足/被安全中心拦截 | 先卸载旧版，清理空间后重试 |
| 校验值不一致 | 下载不完整或被篡改 | 重新下载并再次比对 SHA-256 |

## 三、Android 版说明（主推）

### 界面与交互
- **SafeArea 顶栏**：顶栏自动避让手机状态栏/刘海，绝对不会被系统栏遮挡；顶栏加高（触控友好，含 APP 名 + 当前页面 + 副标题）；
- **返回键**：进入课程 → 作业 → 题目时逐级压栈，按手机返回键**返回上一级菜单**；在根菜单（仪表盘/课程/设置）连按两次返回才退出；
- 底部导航：仪表盘 / 课程 / 设置；每页提供显式返回箭头，操作与系统返回键一致。

### 功能范围（v3.2）
| 功能 | 支持 |
|---|---|
| 登录 / 记住账号 | ✅（保存于 App 本地存储） |
| 仪表盘：待激活 / 已完成 / 平均分 | ✅（服务器真实数据） |
| 课程 → 作业 → 题目浏览 | ✅ |
| 题目图片在线查看 | ✅ |
| 成绩提交（0–100） | ✅ |
| Word / PDF 导出 | ❌ 请在桌面版使用 |

### 构建 APK
云端（推荐，仓库已配置 `.github/workflows/android-apk.yml`）：
```bash
gh workflow run android-apk.yml
gh run download -n lgxt-android-apk
```
本地（需 Flutter 3.24.x + Android SDK + JDK 17）：
```bash
pip install flet==0.25.2
cd mobile && flet build apk
```

### 自有签名（可选）
```bash
flet build apk --android-signing-key-store my-release.jks \
  --android-signing-key-store-password <pwd> \
  --android-signing-key-alias <alias> \
  --android-signing-key-password <pwd>
```

## 四、桌面版界面与交互

| 特性 | 说明 |
|---|---|
| 无边框工作台 | 隐藏系统标题栏与最小化/关闭按钮；标题栏拖动、右下角三角缩放、ESC 退出（代码雨） |
| 星点背景 / 悬停光轨 | Canvas 代码绘制，鼠标附近星点向光标汇聚 |
| 课程星图 | 科目 = 恒星系，习题 = 行星；单击恒星展开（懒加载），单击行星进入题目 |
| 金属切角面板 / 透光按钮 | 切角多边形 + 金属描边；按钮悬停光效 + 轻音效（设置页可关） |
| 仪表盘 | 待激活 / 已完成 / 平均分（真实数据） |
| 全屏 / 字体 | 启动最大化；F11 全屏；字体随窗口自适应缩放 |

## 五、桌面版功能教程

### 1. 登录
AUTH 面板输入用户名/密码；勾选「记住密码」写入 Windows 凭据库（keyring）。

### 2. 仪表盘
侧栏 → 仪表盘：待激活（未提交且仍有次数）、已完成（有成绩）、平均分（成绩均值），`REFRESH` 重新统计。

### 3. 课程星图
侧栏 → 课程星图：单击恒星展开/收起（展开时才请求该课程作业）；行星颜色：🟢可提交 / 🟠最后一次 / 🔴已用完 / 🔵已完成；单击行星进入题目。

### 4. 作业 / 题目
- 作业：SEARCH / FILTER（全部·可提交·已用完）/ SORT；右侧 INSPECTOR 显示章节、截止、成绩、尝试次数、状态；
- 题目：三栏（列表 / 题面+图片 / Inspector 答案与成绩提交），‹ › 切换题目。

### 5. 导出与批量
- 目录：`<导出路径>/作业/<课程>(ID_x)/<作业>(ID_y)/题目图片/ + .docx/.pdf`；
- 单作业 INSPECTOR `EXPORT 题目`；当前课程 `EXPORT ALL`；全部课程在星图页 `EXPORT ALL`；
- 批量任务在页面底部 Task Panel 显示进度，图片命中缓存不重复下载。

### 6. 设置
`EXPORT`（Word/PDF、是否含答案）、`PATH`（导出目录）、`UI`（界面音效）；`SYSTEM` 显示 API、版本、许可、登录状态。

## 六、快捷键（桌面版）

| 按键 | 作用 |
|---|---|
| `ESC` | 退出（代码雨特效） |
| `F11` | 全屏 / 还原 |
| 双击标题栏 | 最大化 / 还原工作区 |
| 单击恒星 / 行星 | 展开科目 / 打开题目 |
| 双击作业行 | 打开题目 |

## 七、数据与配置位置

| 内容 | 位置 |
|---|---|
| Windows 配置 | `%APPDATA%\LGXT-Assistant\config.ini`（旧版脚本目录配置自动迁移） |
| Windows 凭据 | Windows 凭据管理器（keyring，不写入配置文件） |
| Android 数据 | 应用沙盒内 `client_storage`（记住的账号密码、设置） |
| 导出 | 桌面版设置页指定目录 |

## 八、常见问题

| 问题 | 处理 |
|---|---|
| 登录失败 | 检查账号密码；错误提示区分「网络错误 / 非 JSON 响应 / 缺少字段」 |
| 星图展开失败 | 确认网络后再次单击该恒星重试 |
| 图片显示失败 | 提示 `[ IMAGE ERROR ]`，重新进入题目页重试 |
| 导出失败 | 检查导出路径是否可写；结果弹窗会列出原因 |
| 手机返回直接退出？ | v3.2 起：返回键回上一级；根菜单连按两次才退出 |
| 顶栏被状态栏遮挡？ | v3.2 起使用 SafeArea，自动避让状态栏/刘海 |
| 没有声音 | 桌面版设置页 `UI` 分组开启界面音效 |
| 想用 HTTPS | 设置环境变量 `LGXT_API_BASE=https://<host>/api` 后启动 |

## 九、项目结构

```
default.pyw         Windows 入口
theme.py / ui/      Windows 桌面 UI（宇宙星链：base/widgets/space/dashboard/页面 mixin）
api.py / tasks.py / exporter.py / config.py
mobile/             Android (Flet) 工程
  ├── pyproject.toml
  └── src/main.py   SafeArea 顶栏 / 视图栈返回 / 登录 / 仪表盘 / 课程 / 作业 / 题目
tests/              pytest（23 项）
packaging/          PyInstaller / WiX MSI / 代码签名脚本
.github/workflows/  android-apk.yml（云端构建 APK）
docs/screenshots/   README 截图
```

## 十、开发与测试

```bash
pip install -r requirements-dev.txt
python -m pytest
python -m compileall default.pyw theme.py api.py config.py exporter.py tasks.py ui tests
```

## 十一、打包（Windows）

```powershell
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1
# 产物：dist\LGXT-Assistant.exe（单文件）、dist\LGXT-Assistant-portable.zip（便携版）
```

## 十二、Windows 安装包（MSI）

```powershell
# 先构建便携版，再用 WiX v3 生成 MSI
powershell -ExecutionPolicy Bypass -File packaging\build_msi.ps1 -WixBin <wix3 目录>
```

## 十三、代码签名

```powershell
powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 `
  -Path dist\LGXT-Assistant.exe, dist\LGXT-Assistant-3.2.0-setup.msi `
  -Thumbprint <证书指纹>
```
- 当前产物为**自签名证书**签名，Windows 仍会提示「未知发布者」（预期）；
  要消除 SmartScreen 提示需购买 CA 签发的代码签名证书后重新签名。
- 公钥：`packaging/LGXT-Assistant-SelfSigned.cer`；仅测试用途。

## 十四、许可

GPL-3.0-or-later，详见 [LICENSE](LICENSE)。
本工具仅限学习交流使用，请勿转卖或用于商业用途。
Author: Styayur
