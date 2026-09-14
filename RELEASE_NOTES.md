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

两种产物均由 PyInstaller 打包，内置 Python 运行时与全部依赖（ttkbootstrap 主题、
Pillow、python-docx、reportlab、keyring 等），**在未安装 Python 的 Windows 电脑上可直接运行**。
已在剥离 Python 环境变量的条件下实测通过。

源码运行：
```bash
pip install -r requirements.txt
python default.pyw
```

## 快捷操作
- `ESC` 退出（代码雨）
- `F11` 全屏 / 还原
- 单击恒星展开科目 → 单击行星打开题目

## 许可
GPL-3.0-or-later · 仅限学习交流使用，请勿转卖或用于商业用途 · Author: Styayur
