# LGXT Assistant · 理工学堂助手（v3.2.1）

面向理工学堂平台的桌面与移动工具：查看课程与作业、浏览题目、导出题目、提交成绩。

- **Android（主推）**：`LGXT-Assistant-3.2.1-android.apk` — 手机直接安装，无需 Python
- **Windows**：MSI 安装包 / 单文件 exe / 便携版 zip
- **在线教程**：https://styayur.github.io/LGXT-Assistant/
- **Release**：https://github.com/styayur/LGXT-Assistant/releases

---

## 一、下载与安装（按平台）

### 1. Android（推荐）

1. 打开 [Releases](https://github.com/styayur/LGXT-Assistant/releases) 下载 `LGXT-Assistant-3.2.1-android.apk`；
2. 手机「设置 → 应用 → 特殊应用权限 → 安装未知应用」，允许浏览器 / 文件管理器安装；
3. 点击 APK 完成安装（系统要求 Android 7.0+，支持 arm64-v8a / armeabi-v7a / x86_64）；
4. 打开应用 → 输入理工学堂账号密码 → 登录。

> 顶部栏使用 SafeArea，自动避让状态栏 / 刘海；手机返回键返回上一级菜单，
> 在根菜单（仪表盘 / 课程 / 设置）连按两次返回才退出。

### 2. Windows — MSI 安装包（推荐）

1. 下载 `LGXT-Assistant-3.2.1-setup.msi`，双击安装（**用户级，无需管理员**）；
2. 从开始菜单「LGXT Assistant」启动；
3. 卸载：设置 → 应用 → 已安装的应用 → LGXT Assistant。
   命令行：`msiexec /x LGXT-Assistant-3.2.1-setup.msi /qn /norestart`

### 3. Windows — 单文件 / 便携版

- `LGXT-Assistant.exe`：双击运行（首次启动稍慢）；SmartScreen 提示时选「更多信息 → 仍要运行」；
- `LGXT-Assistant-portable.zip`：解压到普通目录 → 双击 `LGXT-Assistant-portable.exe`（启动更快，可放 U 盘）。

### 4. 校验与签名（可选）

```powershell
# 校验下载文件（与 SHA256SUMS.txt 比对）
Get-FileHash .\LGXT-Assistant-3.2.1-android.apk -Algorithm SHA256
certutil -hashfile LGXT-Assistant.exe SHA256

# 查看 Authenticode 签名
Get-AuthenticodeSignature .\LGXT-Assistant.exe | Format-List Status,SignerCertificate
```

- Windows 产物目前使用**自签名证书**签名：状态显示 `UnknownError` 属预期，SmartScreen 仍会提示未知发布者；
- 消除提示需购买 CA 签发的代码签名证书后重新签名（见第九节）；
- 自签名公钥：`LGXT-Assistant-SelfSigned.cer`（仅测试用途）。

---

## 二、Android 版使用步骤

1. **登录**：输入用户名与密码；勾选「记住账号密码」可保存到本机 App 存储；
2. **仪表盘**：查看「待激活 / 已完成 / 平均分」，点 `REFRESH` 重新统计（数据来自服务器真实返回）；
3. **课程**：底部导航「课程」→ 选择科目；
4. **作业**：显示作业名称、剩余次数 / 已完成 / 已用完、截止时间；点「查看题目」进入；
5. **题目**：查看题面与图片，右下方输入 0–100 并点 `SUBMIT` 提交成绩；
6. **返回**：页面左上返回箭头或手机返回键，逐级返回上一级菜单；
7. **设置**：查看 API、版本、许可与登录状态，可退出登录。

> 移动端 v3.2.1 不包含 Word / PDF 导出，请在 Windows 版导出。

---

## 三、Windows 版使用步骤

1. **登录**：AUTH 面板输入账号密码，可勾选「记住密码」（写入 Windows 凭据管理器）；
2. **仪表盘**：侧栏「仪表盘」查看待激活 / 已完成 / 平均分；
3. **课程星图**：侧栏「课程星图」→ 单击恒星展开该科目的作业行星（按需加载）；
   行星颜色：绿=可提交、橙=仅剩最后一次、红=已用完、蓝=已完成；单击行星进入题目；
4. **作业工作区**：左侧 Search / Filter / Sort；右侧 Inspector 显示章节、截止、成绩、尝试次数与状态；
5. **题目三栏**：左列表、中题面图片、右 Inspector（答案 + 成绩提交）；
6. **导出**：单作业 `EXPORT 题目`、当前课程 `EXPORT ALL`、全部课程在星图页 `EXPORT ALL`；
   目录：`<导出路径>/作业/<课程>(ID_x)/<作业>(ID_y)/`（含 `题目图片`、`.docx`、`.pdf`）；
7. **设置**：导出格式与是否含答案、导出路径、界面音效；右侧 SYSTEM 显示 API / 版本 / 许可 / 登录状态。

### 桌面快捷键

| 快捷键 | 作用 |
|---|---|
| `ESC` | 退出（代码雨特效） |
| `F11` | 全屏 / 还原 |
| `Ctrl+R` | 刷新当前页面 |
| 双击标题栏 | 最大化 / 还原工作区 |
| 双击作业行 | 打开题目 |

---

## 四、Release 文件清单

| 文件 | 平台 | 说明 |
|---|---|---|
| `LGXT-Assistant-3.2.1-android.apk` | Android | 手机版（主推），侧载安装 |
| `LGXT-Assistant-3.2.1-setup.msi` | Windows | 用户级安装包，含开始菜单快捷方式与卸载项 |
| `LGXT-Assistant.exe` | Windows | 单文件版 |
| `LGXT-Assistant-portable.zip` | Windows | 便携版（解压即用） |
| `LGXT-Assistant-SelfSigned.cer` | Windows | 自签名公钥（可选） |
| `SHA256SUMS.txt` | 通用 | 全部文件的 SHA-256 校验值 |

下载链接规则：`https://github.com/styayur/LGXT-Assistant/releases/download/v3.2.1/<文件名>`

---

## 五、常见问题

| 问题 | 处理 |
|---|---|
| 手机安装被拦截 | 允许「安装未知应用」；若提示「应用未安装」，先卸载旧版本并清理空间 |
| 登录一直显示 CONNECTING | v3.2.1 已修复（超时 20s 自动提示，可取消 / 重试）；仍失败请检查网络与服务端 |
| Windows 提示未知发布者 | 自签名证书所致，选「更多信息 → 仍要运行」，或用自有证书签名 |
| 星图展开失败 | 确认网络后再次单击该恒星重试 |
| 导出失败 | 检查导出目录是否可写；结果弹窗会给出失败原因 |
| 想用 HTTPS | 设置环境变量 `LGXT_API_BASE=https://<host>/api` 后启动 |

---

## 六、项目结构

```
default.pyw            Windows 入口（tkinter / ttkbootstrap）
theme.py / ui/         桌面 UI（base / widgets / space / dashboard / 页面 mixin）
api.py tasks.py exporter.py config.py
mobile/                Android（Flet + Flutter）
  ├── pyproject.toml
  └── src/main.py      SafeArea 顶栏 / 视图栈返回 / 登录 / 仪表盘 / 课程 / 作业 / 题目
docs/                  GitHub Pages 教程网页（index.html）与截图
tests/                 pytest 测试集
packaging/             PyInstaller / WiX MSI / 代码签名脚本
.github/workflows/     android-apk.yml（云端构建 APK）、tests.yml（pytest）
```

---

## 七、开发与构建

```bash
# 桌面版依赖与运行
pip install -r requirements.txt
python default.pyw

# 测试
pip install -r requirements-dev.txt
python -m pytest

# Android APK（云端，推荐）
gh workflow run android-apk.yml
gh run download -n lgxt-android-apk

# Android APK（本地，需要 Flutter 3.24.x + Android SDK + JDK 17）
pip install flet==0.25.2
cd mobile && flet build apk

# Windows 打包
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1

# Windows MSI（需要 WiX v3 免安装二进制）
powershell -ExecutionPolicy Bypass -File packaging\build_msi.ps1 -WixBin <wix3 目录>
```

---

## 八、数据与配置

| 内容 | 位置 |
|---|---|
| Windows 配置 | `%APPDATA%\LGXT-Assistant\config.ini` |
| Windows 凭据 | Windows 凭据管理器（keyring） |
| Android 数据 | 应用沙盒内 `client_storage` |
| 导出 | Windows 版设置页指定目录 |

---

## 九、代码签名

```powershell
powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 `
  -Path dist\LGXT-Assistant.exe, dist\LGXT-Assistant-3.2.1-setup.msi `
  -Thumbprint <证书指纹>
```

- 当前使用自签名证书，Windows 显示「未知发布者」属预期；
- 正式发布请购买 CA 代码签名证书（OV/EV），用上面的脚本重新签名即可消除 SmartScreen 提示。

---

## 十、许可

GPL-3.0-or-later，详见 [LICENSE](LICENSE)。本工具仅限学习交流使用，请勿转卖或用于商业用途。
Author: Styayur
