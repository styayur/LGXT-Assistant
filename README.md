# LGXT Assistant（理工学堂助手）v3.0

理工学堂助手是一个面向理工学堂平台的桌面小工具：登录后查看课程与作业、
浏览题目、将作业题目（含图片与答案）导出为 Word / PDF，并支持批量提交成绩。

本版本在保留既有功能、业务逻辑、API 行为与交互流程的前提下，完成代码精简
重构与 Developer Tool 风格的 UI/UX 视觉升级。

## 运行

环境要求：Python 3.7+（Windows）。

```bash
pip install -r requirements.txt
python default.pyw
```

## 功能

- 登录：用户名 + 密码，支持记住密码（本地凭据库）。
- 课程 / 作业：查看当前课程与作业列表（含剩余次数、截止时间、章节、成绩）。
- 题目：查看题目图片与答案，可单个提交成绩（0-100）。
- 导出：将作业题目导出为 Word / PDF，可包含答案与题目图片。
- 批量：一键将全部课程（或当前课程）的作业成绩提交为 100 分；批量导出
  全部课程（或当前课程）的作业。

## 依赖

```txt
keyring
requests
ttkbootstrap
Pillow
python-docx
reportlab
```

## 许可

GPL-3.0-or-later，详见 LICENSE。本工具仅限学习交流使用，请勿转卖或用于商业用途。
