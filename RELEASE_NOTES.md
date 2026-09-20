# LGXT Assistant v3.2.0 — 主推 Android 移动版

## 本次更新（移动端）

- **SafeArea 顶栏**：顶栏自动避让手机状态栏 / 刘海，不再被系统栏遮挡；顶栏加高（APP 名 + 当前页面 + 副标题），触控更友好
- **返回键导航**：进入 课程 → 作业 → 题目 时逐级压栈，手机返回键**返回上一级菜单**；
  根菜单（仪表盘/课程/设置）连按两次返回才退出应用
- 视图栈重写：根级用底部导航（仪表盘 / 课程 / 设置），详情页带显式返回箭头，与系统返回键行为一致
- 版本号统一升级为 **v3.2.0**（桌面端同步升级打包）

## 下载（Android 优先，无需 Python）

| 资产 | 平台 | 说明 |
|---|---|---|
| `LGXT-Assistant-3.2.0-android.apk` | Android | **推荐**：下载 → 允许安装未知应用 → 安装（Android 7.0+，arm64/armv7/x86_64） |
| `LGXT-Assistant-3.2.0-setup.msi` | Windows | 用户级安装（无需管理员），开始菜单快捷方式，可在「设置 → 应用」卸载 |
| `LGXT-Assistant.exe` | Windows | 单文件版：双击运行；SmartScreen 提示时「更多信息 → 仍要运行」 |
| `LGXT-Assistant-portable.zip` | Windows | 便携版：解压后运行 `LGXT-Assistant-portable.exe`，启动更快 |
| `LGXT-Assistant-SelfSigned.cer` | Windows | 自签名公钥证书（可选，仅测试用途） |
| `SHA256SUMS.txt` | 通用 | 全部文件 SHA-256 校验值 |

每个文件的完整下载 / 安装 / 卸载 / 校验步骤见 README「二、Release 文件使用方法（全部资产）」。

## Android 版功能

- 登录（记住账号密码，保存于 App 本地存储）
- 仪表盘：待激活 / 已完成 / 平均分（服务器真实数据）
- 课程 → 作业 → 题目浏览，题目图片在线查看
- 成绩提交（0–100）
- 移动端 v3.2 **不含 Word/PDF 导出**（请在桌面版使用）

## SHA-256 校验

| 文件 | SHA-256 |
|---|---|
| `LGXT-Assistant-3.2.0-android.apk` | `dfd711c7f3938cf22129a1a75f5cbdf4568522568f763c1d555070344b4c4a2b` |
| `LGXT-Assistant.exe` | `3941ea111984318eac6c666e2066b867a0c3d945b305f414979b3798a4e62bde` |
| `LGXT-Assistant-portable.zip` | `eea6abde380886603f640df38268aeedc8be2b2da65dd2988d05a73c3323625f` |
| `LGXT-Assistant-3.2.0-setup.msi` | `075ce80b7625d0a820f515b00d46387c7bc304d2096efb74509bf558a3015775` |
| `LGXT-Assistant-SelfSigned.cer` | `cdea811ab5b8b846e838fa25550efe948bee7ac7e98701060a5b7528d74bcd2f` |

```powershell
Get-FileHash .\LGXT-Assistant-3.2.0-android.apk -Algorithm SHA256
```

## 构建说明

- **Android APK**：Flet 0.25.2（Python + Flutter），由 GitHub Actions `.github/workflows/android-apk.yml` 云端构建（Flutter 3.24.5 + Android SDK 37 + JDK 17）
- **Windows**：PyInstaller（单文件 / 便携版）+ WiX v3（MSI），Authenticode 自签名
- 应用内版本号：`v3.2.0`（桌面端与移动端一致）

## 许可

GPL-3.0-or-later · 仅限学习交流使用，请勿转卖或用于商业用途 · Author: Styayur
