# LGXT Assistant v3.2.1

## 版本主题
登录稳定性修复 · Windows 界面现代化 · 移动端体验完善

## 重要修复：登录卡在 CONNECTING
- **根因**：移动端使用 `page.run_task(同步函数)` 触发 Flet 断言失败（Flet 仅接受协程函数），
  登录成功后无法跳转，界面停留在 CONNECTING。
- **修复**：改为线程安全的直接 UI 调度（任意线程调用控件 + `page.update()`），并增加异常兜底。
- **兜底体验**：登录增加 20 秒超时看门狗，超时自动返回登录页并提示；
  CONNECTING 页面提供「取消 / 重试」按钮，不会再出现无法退出的等待状态。
- 同时降低请求重试次数（3→2）与退避时间，弱网下更快给出结果。

## Windows 界面现代化
- 采用现代系统 UI 字体（Segoe UI Variable Text / Segoe UI，自动回退微软雅黑）
- 切角面板新增顶部微高光带（玻璃质感），按钮新增轻投影与更明确的悬停/按下反馈
- 侧栏导航新增左侧 2px 强调条与当前页面高亮状态
- 新增 `Ctrl+R` 刷新当前页面
- 保留宇宙星链视觉（星空、光轨、恒星系/行星、代码雨退出、ESC/F11）

## 移动端（Android）
- 顶栏使用 SafeArea，自动避让状态栏与刘海；顶栏加高，触控更友好
- 返回键逐级返回上一级菜单；根菜单连按两次返回才退出
- 底部导航：仪表盘 / 课程 / 设置；详情页提供显式返回箭头
- 功能：登录、仪表盘（待激活/已完成/平均分）、课程→作业→题目浏览、图片查看、成绩提交
- 移动端不含 Word/PDF 导出（请在 Windows 版导出）

## 产物与校验

| 文件 | 平台 | 说明 |
|---|---|---|
| `LGXT-Assistant-3.2.1-android.apk` | Android | 主推：侧载安装（Android 7.0+，三套 ABI） |
| `LGXT-Assistant-3.2.1-setup.msi` | Windows | 用户级安装包，无需管理员，含开始菜单与卸载项 |
| `LGXT-Assistant.exe` | Windows | 单文件版（已签名） |
| `LGXT-Assistant-portable.zip` | Windows | 便携版（已签名主程序） |
| `LGXT-Assistant-SelfSigned.cer` | Windows | 自签名公钥（可选，仅测试） |
| `SHA256SUMS.txt` | 通用 | 全部文件 SHA-256 校验值 |

```powershell
Get-FileHash .\LGXT-Assistant-3.2.1-android.apk -Algorithm SHA256
Get-AuthenticodeSignature .\LGXT-Assistant.exe | Format-List Status,SignerCertificate
```

## 安装提示
- **Android**：允许「安装未知应用」后点击 APK；提示「应用未安装」时先卸载旧版本并清理空间。
- **Windows MSI**：双击安装；卸载用「设置 → 应用」或
  `msiexec /x LGXT-Assistant-3.2.1-setup.msi /qn /norestart`。
- Windows 产物使用自签名证书，SmartScreen 会提示未知发布者（预期）；
  消除提示需购买 CA 代码签名证书后用 `packaging/sign.ps1` 重新签名。

## 构建
- Android：Flet 0.25.2 + Flutter 3.24.5 + Android SDK 37 + JDK 17，由 GitHub Actions 云端构建
- Windows：PyInstaller（单文件 / 便携版）+ WiX v3（MSI）+ Authenticode 签名
- 测试：GitHub Actions `tests.yml` 在 windows-latest 运行 pytest

## 许可
GPL-3.0-or-later · 仅限学习交流使用，请勿转卖或用于商业用途 · Author: Styayur
