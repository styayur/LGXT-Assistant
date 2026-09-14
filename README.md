# LGXT Assistant · 理工学堂助手

> 一个面向理工学堂平台的 Windows 桌面工具：课程星图浏览、作业与题目查看、
> Word/PDF 导出（含答案与题目图片）、单个/批量成绩提交。
>
> 界面为 **宇宙星链 / Developer Workbench** 风格：无边框工作台、代码绘制的星点背景、
> 悬停光轨、科目恒星系与行星习题、金属切角面板、深色透光按钮（悬停光效 + 轻音效）、
> 仪表盘统计，以及退出时的代码雨特效。

![Star Map](docs/screenshots/starmap_1280.png)
![Dashboard](docs/screenshots/dashboard_1280.png)
![Courses](docs/screenshots/courses_1280.png)
![Works + Inspector](docs/screenshots/works_sel_1280.png)
![Questions](docs/screenshots/questions_1280.png)
![Matrix Rain](docs/screenshots/matrix_rain_1280.png)

---

## 一、快速开始

### 1. 直接运行（推荐）
从 Releases 下载 `LGXT-Assistant.exe`，双击运行，无需安装 Python。

### 2. 从源码运行
```bash
pip install -r requirements.txt
python default.pyw
```
环境：Windows + Python 3.7 及以上。

## 二、Release 文件使用方法（全部资产）

Release 页面：<https://github.com/styayur/LGXT-Assistant-3.0/releases/tag/v3.1.0>

下载链接规则：`https://github.com/styayur/LGXT-Assistant-3.0/releases/download/v3.1.0/<文件名>`

| 资产 | 平台 | 用途 |
|---|---|---|
| `LGXT-Assistant.exe` | Windows | 单文件版：下载双击即用（无需 Python） |
| `LGXT-Assistant-portable.zip` | Windows | 便携版：解压即用，启动更快，可放 U 盘 |
| `LGXT-Assistant-3.1.0-setup.msi` | Windows | 安装包：用户级安装、开始菜单快捷方式、可卸载 |
| `LGXT-Assistant-3.1.0-android.apk` | Android | 手机版：侧载安装（Android 7.0+） |
| `LGXT-Assistant-SelfSigned.cer` | Windows | 自签名公钥证书（可选，用于本机验证签名） |
| `SHA256SUMS.txt` | 通用 | 所有文件的 SHA-256 校验值 |

### 1. `LGXT-Assistant.exe`（Windows 单文件版）
1. 下载后放到任意目录（如桌面），双击运行；
2. 若出现 SmartScreen「Windows 已保护你的电脑」：点「更多信息」→「仍要运行」
   （原因：当前为自签名证书，未购买 CA 证书，详见第十三节）；
3. 首次启动稍慢（单文件需要解压运行时），随后正常；
4. 配置写在 `%APPDATA%\LGXT-Assistant\config.ini`；凭据写入 Windows 凭据管理器；
5. 卸载：直接删除该 exe 即可（无系统残留；如需清理配置，删除上述目录）。

### 2. `LGXT-Assistant-portable.zip`（Windows 便携版）
1. 解压到**非系统保护目录**（如 `D:\LGXT`、U 盘根目录），不要在压缩包里直接运行；
2. 双击 `LGXT-Assistant-portable.exe` 启动（启动速度快于单文件版）；
3. 整个文件夹可整体拷贝/移动，适合多机或离线使用；
4. 卸载：删除整个文件夹即可。

### 3. `LGXT-Assistant-3.1.0-setup.msi`（Windows 安装包）
推荐方式（图形界面）：双击 MSI → 按提示完成安装（**用户级安装，不需要管理员权限**），
安装完成后从开始菜单「LGXT Assistant」启动。

命令行方式：

```powershell
# 安装（静默）
msiexec /i LGXT-Assistant-3.1.0-setup.msi /qn /norestart
# 卸载（静默）
msiexec /x LGXT-Assistant-3.1.0-setup.msi /qn /norestart
```

- 安装位置：`%LOCALAPPDATA%\Programs\LGXT Assistant`
- 卸载也可在「设置 → 应用 → 已安装的应用」中点击卸载
- 安装/卸载实测：exit code 0，目录与开始菜单快捷方式均正确创建/清理

### 4. `LGXT-Assistant-3.1.0-android.apk`（Android 手机版）
1. 用手机浏览器打开 Release 页面下载 APK（或从电脑传输到手机）；
2. 首次安装需允许「安装未知应用」：
   设置 → 应用 → 特殊应用权限 → 安装未知应用 → 允许浏览器/文件管理器；
3. 点击 APK 安装；若提示「应用未安装」：
   - 先卸载同包名的旧版本，再重试；
   - 确认手机剩余存储空间 ≥ 200 MB；
   - 部分机型需关闭「外部来源应用检查」或安全中心的拦截提示；
4. 支持 ABI：`arm64-v8a` / `armeabi-v7a` / `x86_64`（Android 7.0+）；
5. 功能：登录、仪表盘（待激活/已完成/平均分）、课程→作业→题目浏览、
   图片查看、成绩提交、设置；**移动端 v1 不含 Word/PDF 导出**（请在桌面版导出）；
6. 卸载：长按图标 → 卸载（应用数据一并清除）。

### 5. `LGXT-Assistant-SelfSigned.cer`（代码签名公钥，可选）
用途：本机导入后可验证当前产物的签名者身份（**仅用于测试，不建议在生产环境信任**）。

```powershell
# 查看证书信息（不导入）
Get-PfxCertificate .\LGXT-Assistant-SelfSigned.cer | Format-List Subject,Thumbprint,NotAfter

# 导入当前用户「受信任的根证书颁发机构」（导入后签名状态会变为 Valid）
Import-Certificate -FilePath .\LGXT-Assistant-SelfSigned.cer `
  -CertStoreLocation Cert:\CurrentUser\Root
```

验证签名：

```powershell
Get-AuthenticodeSignature .\LGXT-Assistant.exe | Format-List Status,SignerCertificate
# 未导入证书时：Status = UnknownError（签名有效但根证书不受信任，属预期）
```

### 6. `SHA256SUMS.txt`（完整性校验，推荐）
下载所有需要的文件与 `SHA256SUMS.txt` 放在同一目录，然后：

```powershell
# 逐文件校验（PowerShell 7）
Get-FileHash .\LGXT-Assistant.exe -Algorithm SHA256
# 与 SHA256SUMS.txt 中对应行比对

# 或使用 certutil（Windows 自带）
certutil -hashfile LGXT-Assistant-3.1.0-setup.msi SHA256
```

本版本校验值（与 `SHA256SUMS.txt` 一致）：

| 文件 | SHA-256 |
|---|---|
| `LGXT-Assistant.exe` | `a2d133069235497691a680f7aab982f5dcf7be8ed0cb69c33e23a0d327c5da5d` |
| `LGXT-Assistant-portable.zip` | `489b92c6e89f7dba91109887fc35bfe98a4cbe7bcc2596471ad2fa9c0c5472b8` |
| `LGXT-Assistant-3.1.0-setup.msi` | `1e03215f09b56a3cc6fbc7b70f09089dd169592cde55949c491c443ba5bae650` |
| `LGXT-Assistant-3.1.0-android.apk` | `e8dd83b7797113b16e56f835d331658599eaf526ad8873663ab21e7e5831ac8f` |
| `LGXT-Assistant-SelfSigned.cer` | `cdea811ab5b8b846e838fa25550efe948bee7ac7e98701060a5b7528d74bcd2f` |

### 7. 常见拦截与处理
| 现象 | 原因 | 处理 |
|---|---|---|
| Windows 提示「未知发布者」 | 使用自签名证书（未购买 CA 证书） | 点「更多信息 → 仍要运行」，或按第十三节用自有证书重新签名 |
| 手机提示「禁止安装」 | Android 默认禁止未知来源 | 允许浏览器/文件管理器安装未知应用 |
| 手机提示「应用未安装」 | 旧版本包名冲突/空间不足/被安全中心拦截 | 先卸载旧版，清理空间后重试 |
| 校验值不一致 | 下载不完整或被篡改 | 重新下载并再次比对 SHA-256 |

## 三、界面与交互

| 特性 | 说明 |
|---|---|
| 无边框工作台 | 隐藏系统原生标题栏与最小化/关闭按钮；标题栏可拖动，右下角三角可缩放 |
| 退出方式 | **ESC** 退出（先播放约 1.8s 代码雨）；也可点侧栏「退出」 |
| 全屏 | **F11** 在「全屏 / 工作区」间切换；双击标题栏最大化工作区 |
| 星点背景 | 全部由 Canvas 代码绘制：星点持续漂浮闪烁 |
| 悬停光轨 | 鼠标靠近星点时，附近星点产生向光标汇聚的青色光轨 |
| 金属切角 | 面板/按钮使用硬朗切角多边形 + 双色金属描边（无圆角、无系统边框） |
| 透光按钮 | 深色透光切角按钮；悬停出现光效并播放轻音效（设置页可关闭） |

## 四、功能教程

### 1. 登录
AUTH 面板输入用户名/密码；勾选「记住密码」写入 Windows 凭据库（keyring）。
登录成功后右上角显示 `● CONNECTED`。

### 2. 仪表盘
侧栏 → **仪表盘**：
- **待激活 PENDING**：尚未提交且仍有剩余次数的作业数量；
- **已完成 DONE**：已有成绩的作业数量；
- **平均分 AVG**：已完成作业成绩的算术平均；
- 下方显示作业总数与读取失败的课程；`REFRESH` 重新统计。

> 所有数字均来自服务器真实返回，不做任何推测或伪造。

### 3. 课程星图（科目 = 恒星系，习题 = 行星）
侧栏 → **课程星图**：
- 每颗恒星代表一门课程；**单击恒星**展开/收起其习题行星（展开时才请求该课程作业）；
- 行星颜色：🟢 可提交 / 🟠 仅剩最后一次 / 🔴 已用完 / 🔵 已完成；
- **单击行星**直接进入题目工作区；展开失败时恒星下方显示 `LOAD FAILED`，再次单击可重试；
- 顶部：`SEARCH` 按课程名/ID 过滤，`SORT` 名称或 ID 排序，`REFRESH` 重新同步；
- 右侧：`EXPORT ALL` 导出全部课程、`SUBMIT ALL 100` 批量提交全部课程。

### 4. 作业工作区（List + Inspector）
- 左列表：`SEARCH`（作业名/章节/ID）、`FILTER`（全部/可提交/已用完）、`SORT`（截止时间/剩余/名称）；
- 右侧 **INSPECTOR**：ID、章节、截止时间、成绩、尝试次数、状态（DONE/EXHAUSTED）；
- `OPEN ▸ 题目` 进入题目页（或双击列表行）；`EXPORT 题目` 单独导出该作业；
- 顶部 `EXPORT ALL` / `SUBMIT ALL 100` / `REFRESH` 作用于当前课程。

### 5. 题目工作区（三栏）
- 左：题目列表（`SEARCH` 题名/答案/ID、`FILTER` 全部/有答案/无图片、`SORT` 编号/名称）；
- 中：题面名称、ID 与图片（后台下载，内存 + 文件双层缓存）；
- 右：**INSPECTOR** 显示答案，输入 0–100 后 `SUBMIT` 提交该作业成绩；
- `‹` / `›` 切换题目，页头 `‹ 返回作业列表` 返回。

### 6. 导出
- 目录结构：`<导出路径>/作业/<课程名>(ID_x)/<作业名>(ID_y)/`
  - `题目图片/<题目ID>.png`
  - `<作业名>.docx`、`<作业名>.pdf`（可选含答案）
- 同一作业重复导出时，已存在且非空的图片会跳过下载；
- 批量任务在页面底部 **Task Panel** 显示进度，完成后弹出结果汇总。

### 7. 设置与帮助
- `EXPORT`：Word/PDF 与是否含答案；`PATH`：导出目录；`UI`：界面音效开关；
- `SAVE` 保存（写入 `%APPDATA%\LGXT-Assistant\config.ini`）；`USER INFO` 查看账号信息；
- 右侧 `SYSTEM` 面板显示 API 地址、版本、许可与登录状态；
- 帮助窗口包含：界面与窗口、星图、仪表盘、作业/题目、导出、快捷键、常见问题与声明。

## 五、快捷键

| 按键 | 作用 |
|---|---|
| `ESC` | 退出（代码雨特效） |
| `F11` | 全屏 / 还原 |
| 双击标题栏 | 最大化 / 还原工作区 |
| 单击恒星 / 行星 | 展开恒星系 / 打开题目 |
| 双击作业行 | 打开题目 |

## 六、数据与配置位置

| 内容 | 位置 |
|---|---|
| 配置 | `%APPDATA%\LGXT-Assistant\config.ini`（旧版脚本目录配置自动迁移） |
| 凭据 | Windows 凭据管理器（keyring，不写入配置文件） |
| 导出 | 设置页指定目录（默认当前工作目录） |

## 七、常见问题

| 问题 | 处理 |
|---|---|
| 登录失败 | 检查账号密码；错误提示会区分「网络错误 / 非 JSON 响应 / 缺少字段」 |
| 星图展开失败 | 确认网络后再次单击该恒星重试 |
| 图片显示失败 | 提示 `[ IMAGE ERROR ]`；可重新进入题目页重试 |
| 导出失败 | 检查导出路径是否可写；结果弹窗会列出失败原因 |
| 没有声音 | 设置页 `UI` 分组开启「界面音效」 |
| 想用 HTTPS | 设置环境变量 `LGXT_API_BASE=https://<host>/api` 后启动 |

## 八、项目结构

```
default.pyw        启动入口
theme.py           Design Token / 金属切角配色 / 字体缩放
api.py             API 客户端（session、鉴权、错误分类、图片校验）
tasks.py           收集器与批量任务（后台线程 + future 取消）
exporter.py        图片缓存 + Word/PDF 导出
config.py          %APPDATA% 配置 + keyring 凭据（全部容错）
ui/
  base.py          无边框外壳、队列轮询、字体缩放、星点背景、代码雨
  widgets.py       切角金属面板 / 光效按钮 / PageHeader / CommandBar
  space.py         星图（恒星系 = 科目，行星 = 习题，悬停光轨）
  dashboard.py     仪表盘统计
  login.py / courses.py / works.py / questions.py / settings.py / actions.py
tests/             pytest 测试集（23 项）
docs/screenshots/  README / Release 截图
```

线程模型：worker 只把事件写入 `queue.Queue`，主线程用 `after()` 轮询更新 UI；
导出开关在主线程读取为 `ExportOptions` 快照后传入 worker，避免跨线程访问 Tk 变量。

## 九、开发与测试

```bash
pip install -r requirements-dev.txt
python -m pytest           # 23 passed
python -m compileall default.pyw theme.py api.py config.py exporter.py tasks.py ui tests
```

## 十、打包

提供两种产物（均无需安装 Python）：

| 产物 | 说明 |
|---|---|
| `dist/LGXT-Assistant.exe` | 单文件版（onefile），最方便分发，首次启动稍慢 |
| `dist/LGXT-Assistant-portable.zip` | 便携版（onedir 压缩），启动更快，解压即用 |

一键构建（含图标与版本资源）：

```powershell
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1
```

等价的手工命令：

```bash
python -m PyInstaller --noconfirm --clean --onefile --noconsole \
  --name LGXT-Assistant --icon assets/icon.ico \
  --version-file packaging/version_info.txt \
  --collect-all ttkbootstrap default.pyw

python -m PyInstaller --noconfirm --clean --onedir --noconsole \
  --name LGXT-Assistant-portable --icon assets/icon.ico \
  --version-file packaging/version_info.txt \
  --collect-all ttkbootstrap default.pyw
```

## 十一、Android 版（APK）

移动端使用 **Flet（Python + Flutter）** 实现，通过 GitHub Actions 云端构建（无需本机 Android SDK）。

### 下载安装
1. 从 Releases 下载 `LGXT-Assistant-3.1.0-android.apk`
2. 手机上允许"安装未知应用"后点击安装（APK 已签名，支持直接侧载）
3. 支持 Android 7.0+，ABI：arm64-v8a / armeabi-v7a / x86_64

### 移动端功能
- 登录（记住账号密码，保存在应用本地存储 `client_storage`）
- 仪表盘：待激活 / 已完成 / 平均分（真实 API 统计）
- 课程 → 作业 → 题目浏览，题目图片在线查看
- 成绩提交（0–100），错误提示与桌面版一致的语义
- 深色宇宙主题、导航栏（仪表盘 / 课程 / 设置）

### 与桌面版的差异（v1）
- **不包含 Word / PDF 导出**（Android 上 python-docx/reportlab 的原生依赖难以打包）；导出请在桌面版使用
- 不做本地文件写盘，改为在线查看题目与提交成绩
- APK 当前使用构建时生成的调试签名；如需上架应用商店或长期发布，请用自有 keystore 做 release 签名（见下）

### 构建 APK
云端（推荐，仓库已配置工作流 `.github/workflows/android-apk.yml`）：
```bash
gh workflow run android-apk.yml          # 触发构建
gh run download -n lgxt-android-apk      # 下载 APK 产物
```

本地构建（需要 Flutter 3.24.x + Android SDK + JDK 17）：
```bash
pip install flet==0.25.2
cd mobile
flet build apk
# 产物：mobile/build/apk/app-release.apk
```

### 自有签名（可选）
```bash
flet build apk --android-signing-key-store my-release.jks \
  --android-signing-key-store-password <pwd> \
  --android-signing-key-alias <alias> \
  --android-signing-key-password <pwd>
```

## 十二、Windows 安装包（MSI）

提供用户级 MSI 安装包（**无需管理员权限**）：

```powershell
msiexec /i LGXT-Assistant-3.1.0-setup.msi
```

- 安装位置：`%LOCALAPPDATA%\Programs\LGXT Assistant`
- 自动创建开始菜单快捷方式；卸载可在「设置 → 应用」或开始菜单中完成
- 卸载：`msiexec /x LGXT-Assistant-3.1.0-setup.msi`

构建 MSI（WiX Toolset v3 免安装二进制 + 脚本）：

```powershell
# 1) 下载并解压 wix314-binaries.zip（https://github.com/wixtoolset/wix3/releases）
# 2) 先构建便携版（MSI 安装的是便携版目录）
powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1
# 3) 构建 MSI
powershell -ExecutionPolicy Bypass -File packaging\build_msi.ps1 -WixBin <wix3 目录>
```

## 十三、代码签名

```powershell
# 使用已有证书（推荐：CA 签发的代码签名证书）
powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 `
  -Path dist\LGXT-Assistant.exe, dist\LGXT-Assistant-3.1.0-setup.msi `
  -Thumbprint <证书指纹>
# 或使用 PFX
powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 -Path dist\*.exe `
  -PfxPath cert.pfx -PfxPassword (Read-Host -AsSecureString)
```

- 本仓库当前产物使用**自签名证书**签名（用于完整性验证与流程演示），
  因此 Windows 仍会显示"未知发布者"——这是预期行为。
- 若要让 SmartScreen 不再警告，需要购买 **CA 签发的代码签名证书（OV/EV）**，
  然后用上面的 `sign.ps1` 重新签名（脚本会自动尝试 RFC3161 时间戳）。
- 自签名证书公钥已导出：`packaging/LGXT-Assistant-SelfSigned.cer`
  （导入到"受信任的根证书颁发机构"后，本机将显示签名有效；请勿在生产环境这样做）。
- 创建自签名证书（仅开发/测试）：`packaging/new_selfsigned_cert.ps1`

## 十四、许可

GPL-3.0-or-later，详见 [LICENSE](LICENSE)。
本工具仅限学习交流使用，请勿转卖或用于商业用途。
Author: Styayur
