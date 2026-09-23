"""Build the illustrated, end-user-only Windows guide; all fonts are embedded."""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle, KeepTogether

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'output/pdf/LGXT-Assistant-4.0.1-User-Guide.pdf'
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('Guide','C:/Windows/Fonts/msyh.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('GuideBold','C:/Windows/Fonts/msyhbd.ttc',subfontIndex=0))
pdfmetrics.registerFontFamily('Guide',normal='Guide',bold='GuideBold',italic='Guide',boldItalic='GuideBold')
INK=colors.HexColor('#263249');MUTED=colors.HexColor('#59667b');BLUE=colors.HexColor('#365d9e');LINE=colors.HexColor('#dbe2ed')
PAGE_W,PAGE_H=A4;WIDTH=PAGE_W-92
styles={
 'body':ParagraphStyle('body',fontName='Guide',fontSize=10,leading=18,textColor=INK,wordWrap='CJK',spaceAfter=9),
 'small':ParagraphStyle('small',fontName='Guide',fontSize=8.2,leading=14,textColor=MUTED,wordWrap='CJK',spaceAfter=8),
 'h1':ParagraphStyle('h1',fontName='GuideBold',fontSize=23,leading=33,textColor=INK,spaceAfter=15),
 'h2':ParagraphStyle('h2',fontName='GuideBold',fontSize=13,leading=21,textColor=BLUE,spaceBefore=12,spaceAfter=8),
 'cover':ParagraphStyle('cover',fontName='GuideBold',fontSize=34,leading=47,textColor=INK,spaceAfter=16),
 'cell':ParagraphStyle('cell',fontName='Guide',fontSize=9,leading=15,textColor=INK,wordWrap='CJK'),
}
story=[]
RELEASE='https://github.com/styayur/LGXT-Assistant/releases/tag/v4.0.1'

def p(text,style='body'):
    return Paragraph(text,styles[style])
def body(text):story.append(p(text))
def heading(text):story.append(p(text,'h2'))
def title(number,text,intro):
    story.append(p(f'使用指南 / {number:02d}','small'));story.append(p(text,'h1'));body(intro)
def newpage():story.append(PageBreak())
def steps(items):
    for i,text in enumerate(items,1):body(f'<b>{i}. </b>{text}')
def note(text):
    t=Table([[p(text,'small')]],colWidths=[WIDTH]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#edf3fd')),('BOX',(0,0),(-1,-1),.5,LINE),('LEFTPADDING',(0,0),(-1,-1),13),('RIGHTPADDING',(0,0),(-1,-1),13),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([Spacer(1,8),t,Spacer(1,10)])
def table(headers,rows,widths):
    data=[[p(escape(x),'cell') for x in headers]]+[[p(x,'cell') for x in row] for row in rows]
    t=Table(data,colWidths=[WIDTH*x for x in widths],repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef8')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),('LINEBELOW',(0,0),(-1,0),.7,LINE),('LINEBELOW',(0,1),(-1,-1),.35,LINE),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]));story.extend([t,Spacer(1,10)])
def shot(name,caption,width=WIDTH):
    from PIL import Image as PILImage
    path=ROOT/'docs/screenshots'/name
    with PILImage.open(path) as im:w,h=im.size
    story.extend([Spacer(1,8),Image(str(path),width=width,height=width*h/w),Spacer(1,7),p(caption,'small')])

story.extend([Spacer(1,28),p('LGXT Assistant','h2'),p('理工学堂助手<br/>使用说明','cover'),p('Windows 桌面版 4.0.1  |  2026 年 9 月','body'),p('从打开软件，到连接课程、理解题目与整理学习资料。','body'),Spacer(1,18)])
shot('modern-dark-1440.png','新版主界面。初次打开时，模型显示“尚未选择模型”属于正常状态。')
note('<b>先选你的目标</b><br/>只看课程或导出题目：登录理工学堂即可，不需要 AI 密钥。<br/>只使用 AI 对话：配置模型即可，不需要登录理工学堂。')
body(f'下载与更新：<link href="{RELEASE}" color="#365d9e">GitHub 官方 Release 页面</link>')

newpage();title(1,'下载后，怎样打开？','适用于 Windows 10 / 11 的 64 位电脑。普通使用者无需安装 Python、Node.js，也无需下载源代码。')
table(['下载的文件','怎么使用'],[
 ['LGXT-Assistant.exe','推荐首次使用者选择。保存到自己的文件夹后双击打开。首次启动需要准备文件，请稍等片刻。'],
 ['LGXT-Assistant-portable.zip','右键选择“全部解压缩”。进入解压后的文件夹，双击 LGXT-Assistant-portable.exe。'],
 ['LGXT-Assistant-4.0.1-User-Guide.pdf','本说明书，可保存在本机随时查阅。'],
 ['Source code (zip / tar.gz)','这是开发用源代码，不是安装包。普通使用者请选择上方的 EXE 或便携版。']],[.42,.58])
heading('便携版必须完整解压')
body('不要在压缩包预览窗口里直接运行，也不要只把 EXE 拖到桌面。主程序必须和 <b>_internal</b> 文件夹放在一起。若希望从桌面打开，请为主程序创建快捷方式。')
heading('如果提示缺少 WebView2')
body('这是显示新版界面所需的微软组件。在启动帮助中点击“安装 WebView2”，进入微软官网，安装 Evergreen 运行时，完成后重新打开 LGXT Assistant。')
body('<link href="https://developer.microsoft.com/microsoft-edge/webview2/" color="#365d9e">打开微软 WebView2 官方下载页</link>')
note('如果新版界面仍打不开，在“启动帮助”中选择“进入兼容界面”，可先使用课程功能。兼容界面没有新版 AI 对话区。')

newpage();title(2,'认识你的工作空间','左侧负责切换，中间负责阅读与操作，右侧负责查看当前上下文。')
shot('modern-dark-1440.png','窗口较窄时，侧栏会收起。点击左上或右上的面板图标即可再次打开。')
table(['区域','你可以做什么'],[
 ['左侧导航','新建会话；进入学习助手、我的课程、工作区、提示词库和设置；搜索最近会话。'],
 ['中间工作区','阅读回复、查看课程题目、编辑设置；在底部输入问题。'],
 ['右侧上下文','查看待发送文件、当前任务、模型名称、连接状态与任务进度。'],
 ['顶部工具栏','搜索命令、查看模型、导出当前会话，或展开 / 收起右侧面板。']],[.24,.76])
note('关闭窗口使用右上角关闭按钮。Esc 用于关闭弹窗或停止 AI 生成，不会直接退出新版软件。')

newpage();title(3,'连接理工学堂','课程账号与 AI 模型账号是两套独立连接。这里使用你平时登录理工学堂的账号和密码。')
steps(['点击左侧 <b>我的课程</b>，再点击 <b>登录理工学堂</b>。','输入账号与密码。已保存过密码时，可以留空使用该账号的已保存密码。','需要下次方便登录，可勾选 <b>在系统凭据库中记住账号</b>。只在自己的电脑上使用此选项。','点击 <b>登录</b>。连接成功后会显示你的真实课程列表。'])
shot('modern-login.png','登录窗口示意。你的密码不会出现在主界面。',WIDTH*.9)
heading('连接失败或一直等待')
body('登录等待超过约 20 秒后，会显示超时说明并恢复登录按钮。确认网络与账号密码后再试。你也可以随时点击“取消”或按 Esc，返回课程页；已取消的请求不会在稍后自动把你登录进去。')
body('如果网页端理工学堂也无法登录，请先确认平台服务与账号状态。退出课程账号可点击“我的课程”页面右上角的退出登录图标。')

newpage();title(4,'找到课程、作业和题目','课程数据来自理工学堂平台。首次进入、刷新或切换课程时，需要联网读取。')
steps(['在 <b>我的课程</b> 中点击课程卡片。可通过搜索框按课程名称或编号查找。','进入课程后，点击需要查看的作业。可按状态筛选，或按名称、截止时间排序。','点击左侧题目，阅读题目文字与图片。需要时点击 <b>查看答案</b>，再次点击可收起。','点击 <b>向 AI 请教这道题</b>，将题目信息及可用的题目图片带到聊天输入区。检查引用内容后再发送。'])
shot('modern-courses-fixture.png','课程列表界面示意；图中课程和成绩为演示数据，不代表你的账户。')
note('每页最多显示 20 项。没有找到目标时，检查筛选条件和底部页码。“加载学习概览”会汇总课程作业，课程较多时需要一些时间。')

newpage();title(5,'导出题目与提交成绩','先检查设置和作业范围，再执行操作。导出和成绩提交是两个不同的功能。')
heading('导出为 Word 或 PDF')
steps(['打开 <b>设置 → 导出</b>，选择导出目录。建议选择“文档”等自己可以写入的位置。','开启需要的格式：Word、PDF，或同时开启。分别选择是否包含答案，然后点击 <b>保存更改</b>。','只导出一个作业：进入该作业的题目页，点击 <b>导出全部题目</b>。','导出整个课程：在课程作业列表点击 <b>导出课程</b>。在课程首页点击 <b>导出全部课程</b>，会处理所有课程。','等待任务进度结束，阅读“任务结果”中的成功和失败明细，再到你选择的目录查看文件。'])
note('导出文件按“作业 / 课程名称 / 作业名称”组织，并包含题目图片。收集题目时可能发送多次请求，请等待完成；不要把暂时没有新进度误认为任务已经结束。')
heading('提交成绩')
steps(['在题目页找到 <b>提交本作业成绩</b>，输入 0 到 100 的整数。','点击 <b>提交成绩</b>，在确认窗口核对作业名称和分数。确认后才会向平台提交。','批量提交入口位于课程或作业列表底部。请在确认窗口核对范围；批量操作会提交 100 分并消耗对应提交次数。'])
body('只提交你有权提交且已经核实的成绩。若出现失败，先查看结果，避免在不清楚上次是否成功的情况下反复点击。')

newpage();title(6,'第一次使用 AI 对话','AI 功能使用你自己的模型服务。没有设置模型时，课程浏览和导出仍可正常使用。')
steps(['点击输入器中的 <b>选择模型</b>，或进入 <b>设置 → AI 模型</b>。','在 <b>Provider</b> 选择你已开通的服务。把服务提供方给你的接口基础地址填入 <b>API Endpoint</b>。','填入你有权限使用的 <b>模型 ID</b>。模型 ID 不是随意填写的昵称，应以服务提供方显示的名称为准。','填入 <b>API Key</b>。保存后密钥进入系统凭据库；下次留空会保留该服务已有密钥。','点击 <b>保存并测试连接</b>。看到 <b>Connected</b> 表示所选模型已实际返回文本。测试会发送一个简短问题，可能产生少量服务费用。'])
table(['服务','填写提示'],[['OpenAI','填写该账号可用的 GPT 模型 ID 与 API Key。'],['Claude','使用 Claude 服务的模型 ID 与 API Key。'],['Gemini','使用 Gemini 服务的模型 ID，并使用其兼容接口地址。'],['Local','先启动本机模型服务，再填写其接口地址和已安装的模型名称。无认证的本地服务可不填 Key。']],[.24,.76])
heading('调整回复习惯')
body('<b>Temperature</b> 较低时通常更稳定，较高时更有变化。<b>上下文消息数</b> 控制发送多少条最近消息；<b>最大输出 Token</b> 控制回复长度上限。部分模型不接受某些参数，应以模型服务的说明为准。')
note('切换服务不会替你购买模型、开通账号或增加额度。连接失败时，先核对接口地址、模型 ID、密钥和余额。API Key 不要填写到普通聊天消息中。')

newpage();title(7,'发送问题，读懂回复','建议先说明学习目标，再给出题目或资料，以及希望得到的帮助方式。')
steps(['点击左侧 <b>新建会话</b>，在底部输入问题。Enter 用于换行；按 <b>Ctrl + Enter</b> 或点击向上箭头发送。','回复生成时可以边看边读。需要中断时，点击方形停止按钮，或在没有弹窗时按 Esc。已经出现的文字会保留。','消息下方提供复制、编辑或重新生成操作。编辑和重新生成会替换该位置之后的内容，重要记录可先导出。'])
shot('modern-chat-fixture.png','示例会话展示公式、表格和代码排版；内容仅用于说明界面。')
note('AI 可能出错。涉及重要结论、计算与作业答案时，请结合教材或老师提供的资料核实。停止生成后可以修改问题重新发送。')

newpage();title(8,'给 AI 添加学习资料','你决定发送哪些资料。只有附加到消息中的内容，才会随着发送交给所选模型。')
heading('从工作区整理资料')
steps(['打开 <b>工作区</b>，在“当前学习任务”中写下本次目标。当前任务会作为之后发送消息的上下文。','点击 <b>添加资料</b>，选择笔记、代码或题目图片。','在文件卡片上点击 <b>引用到对话</b>。文件会出现在聊天输入器上方。','发送前核对文件名称。点击附件旁的叉号，可将其从这次消息中移除。'])
table(['可以添加','限制与说明'],[['文本和代码','支持 UTF-8 的 .txt、.md、.py、.js、.ts、.json、.csv。长文本最多读取前 60,000 个字符。'],['图片','支持 PNG、JPEG、WebP。要让模型理解图片，所选模型必须支持视觉输入。'],['大小与数量','单个文件不超过 2 MB，一次选择最多 8 个文件。工作区最多 80 个文件，总资料不超过 32 MB。'],['PDF / Word','目前不直接读取这两种文件作为聊天资料。可先复制需要的文字，或把题目截成图片后添加。']],[.25,.75])
heading('资料保存与移除')
body('工作区资料与当前任务保存在本机，重开软件后仍可继续使用。移除工作区资料不会删除你电脑中的原始文件；已经随消息保存的附件仍属于该条会话。')
note('不需要继续发送当前学习任务时，请清空工作区的任务输入框。工作区目前按文件引用使用，不会自动检索所有资料或建立会自动学习的知识库。')

newpage();title(9,'管理会话、模板和学习偏好','把需要重复使用的内容留下，把一次性的内容清理掉。')
heading('会话历史')
body('左侧“最近会话”可以按会话标题搜索。点击会话继续阅读；悬停会话后点击更多按钮，可以重命名或删除。新会话的标题默认取自第一条问题，你可以改成更容易查找的名称。')
body('顶部导出按钮会把当前会话保存为 Markdown 文本，可用文本编辑器查看。导出内容包含消息正文和附件名称，不等于工作区与图片附件的完整备份。')
heading('提示词库')
steps(['打开 <b>提示词库</b>，找到“概念拆解”“分步解题”等模板。','点击 <b>使用模板</b>，模板文字会进入输入器。补充自己的题目再发送。','点击 <b>新建提示词</b>，填写名称和内容后保存。自己的模板支持编辑和删除。'])
heading('长期学习偏好')
body('在 <b>设置 → 记忆与存储</b> 中，填写你希望每次请求都参考的背景，例如“我正在学习大学物理，希望先解释直觉，再展示公式”。开启“在新请求中加入学习偏好”并保存。这里的记忆由你填写和修改，不会自动从历史对话提取。')
heading('是否保存会话')
body('同一设置页可以关闭“在本机保存会话”。关闭后，新消息只保留在当前窗口，关闭软件后不再保留。已经保存的历史不会自动删除，需要在侧栏单独删除。')
note('会话与工作区保存在本机，账号密码和模型密钥保存在系统凭据库。发送给云端模型的消息与附件还会由对应服务处理；添加资料前请确认它适合发送给该服务。')

newpage();title(10,'外观与常用快捷键','在“设置 → 通用”中选择深色、浅色或跟随系统。修改完成后点击“保存更改”。')
shot('modern-settings-light.png','浅色设置界面。减少动态效果适合希望界面更安静、切换更直接的使用者。',WIDTH*.88)
table(['操作','快捷键'],[['搜索功能、会话、模型或文件','Ctrl + K / Ctrl + Shift + P'],['新建会话','Ctrl + N'],['发送消息','Ctrl + Enter'],['输入换行','Enter'],['停止生成 / 关闭当前弹窗','Esc'],['切换全屏 / 还原','F11']],[.62,.38])
body('命令面板支持输入关键词搜索，用上下方向键选择，再按 Enter 执行。保存过模型配置后，可通过“切换模型服务”命令快速切换。')

newpage();title(11,'遇到问题时，按这里处理','先查看软件显示的具体提示。可以取消的等待不必强行结束程序，也不需要反复点击同一按钮。')
table(['现象','建议处理方式'],[
 ['双击后没有进入新版界面','查看“启动帮助”。完整解压便携版，保留 _internal；缺少 WebView2 时从微软官网安装。必要时先进入兼容界面。'],
 ['显示“桌面连接未就绪”','关闭该窗口，再从完整安装包中的主程序打开。不要把网页预览或 Source code 当作桌面程序。'],
 ['显示资料恢复或备份提示','软件已保留异常文件备份并允许继续使用。先新建会话；如需找回旧资料，保留数据目录中的 .bak 文件并联系维护者。'],
 ['登录超时或账号错误','核对账号密码与网络，确认平台网页是否能登录。取消后可重试，不会稍后自动登录。'],
 ['课程列表为空或图片缺失','清空搜索 / 筛选后刷新。检查账号是否选课、作业是否开放，以及平台图片是否能正常访问。'],
 ['AI 连接失败或没有文字','检查接口基础地址、模型 ID、API Key 与服务额度。先测试连接，再发送短问题。图片问题需使用视觉模型。'],
 ['导出失败或找不到文件','确认已开启 Word 或 PDF 并保存设置，检查导出目录写入权限。阅读任务结果中的每项失败原因。'],
 ['窗口较小，找不到导航','点击左上角面板图标展开导航；右侧上下文可单独展开。中间内容可以滚动。']],[.31,.69])
body('仍无法解决时，向维护者提供：使用的版本、Windows 版本、下载的文件名、出错步骤和提示截图。截图前遮住密码、API Key 和不需要公开的个人资料。')

newpage();title(12,'更新、备份与获取帮助','更新前先关闭所有 LGXT Assistant 窗口。下载新版本时，始终确认项目地址为 styayur/LGXT-Assistant。')
heading('更新软件')
steps(['打开官方 Release 页面，下载新版 EXE 或便携 ZIP。','单文件版可放到新的文件夹中运行；便携版请解压到新文件夹，不要只替换其中一个文件。','打开新版后，检查会话、工作区与导出设置。旧版程序文件可以保留到确认新版可用。'])
heading('备份本机资料')
steps(['关闭软件。按 Windows + R 打开“运行”，输入 <b>%APPDATA%\\LGXT-Assistant</b> 并按 Enter。','把整个文件夹复制到你选择的备份位置。它包含会话、工作区和配置资料，可能包含个人内容，请妥善保管。','系统凭据库中的密码和模型密钥不在该文件夹中。换电脑或重新安装系统后，可能需要重新登录并填写 API Key。'])
note('导出目录里的 Word、PDF 和题目图片是单独的文件，也请根据需要备份。不要把删除程序文件理解为已经删除所有学习资料。')
heading('官方入口')
body(f'<link href="{RELEASE}" color="#365d9e">下载 Windows 4.0.1 与本说明书</link><br/><link href="https://github.com/styayur/LGXT-Assistant/issues" color="#365d9e">反馈问题与查看处理进展</link><br/><link href="https://github.com/styayur/LGXT-Assistant/releases/tag/v3.2.1" color="#365d9e">Android 用户：查看 3.2.1 历史版本</link>')
heading('本说明书的适用范围')
body('本说明面向 Windows 桌面版 4.0.1。Android 与兼容界面的布局和功能不同。示例截图中的会话、课程与分数仅用于说明界面；实际内容以你连接的平台和模型返回为准。')
body('LGXT Assistant 由 StyAyur 维护，采用 GPL-3.0-or-later 许可。')

def frame(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(LINE);canvas.setLineWidth(.5)
    canvas.line(46,43,PAGE_W-46,43);canvas.setFont('Guide',8);canvas.setFillColor(MUTED)
    canvas.drawString(46,29,'LGXT Assistant 4.0.1  |  Windows 使用说明')
    canvas.drawRightString(PAGE_W-46,29,str(doc.page))
    if doc.page>1:
        canvas.drawString(46,PAGE_H-30,'理工学堂助手 / 使用说明')
    canvas.restoreState()

doc=SimpleDocTemplate(str(OUTPUT),pagesize=A4,rightMargin=46,leftMargin=46,topMargin=53,bottomMargin=59,title='LGXT Assistant 4.0.1 Windows 使用说明',author='StyAyur',subject='面向使用者的下载、课程、AI 对话与故障排查指南')
doc.build(story,onFirstPage=frame,onLaterPages=frame)
print(OUTPUT)
