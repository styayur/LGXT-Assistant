"""Install and exercise the actual candidate APK with adb/UIAutomator.

No real credentials, grades or model requests. Screenshots contain dummy inputs.
"""
import argparse
import hashlib
import json
import re
import subprocess
import time
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apk',required=True)
    parser.add_argument('--output',default='build/android/device')
    parser.add_argument('--fixture',action='store_true')
    parser.add_argument('--historical-apk')
    parser.add_argument('--backup-roundtrip',action='store_true',help='Import synthetic notes through the ordinary release APK picker')
    args=parser.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    def adb(*args):
        return subprocess.check_output(['adb',*args],timeout=90)
    def shell(*args):return adb('shell',*args).decode('utf-8',errors='replace')
    def screen(name): (out/(name+'.png')).write_bytes(adb('exec-out','screencap','-p'))
    def tree():
        shell('uiautomator','dump','/sdcard/lgxt-acceptance.xml')
        raw=shell('cat','/sdcard/lgxt-acceptance.xml')
        (out/'latest-ui.xml').write_text(raw,encoding='utf-8')
        return ET.fromstring(raw)
    def nodes_containing(root,text):
        return [node for node in root.iter('node') if text.casefold() in (node.get('text','')+' '+node.get('content-desc','')).casefold()]
    def wait_text(text):
        deadline=time.monotonic()+75
        while time.monotonic()<deadline:
            root=tree()
            if nodes_containing(root,text):return root
            time.sleep(1)
        screen('failure')
        raise AssertionError('Android UI not ready: '+text)
    def tap_node(node):
        x1,y1,x2,y2=map(int,re.findall(r'\d+',node.get('bounds')))
        shell('input','tap',str((x1+x2)//2),str((y1+y2)//2))
    def tap_text(text):
        # File-picker return and Flutter dialogs can expose semantics while the
        # entrance animation still moves the touch target. Use settled bounds.
        wait_text(text)
        time.sleep(.6)
        node=nodes_containing(wait_text(text),text)[-1]
        with (out/'actions.txt').open('a',encoding='utf-8') as actions:
            actions.write(f"tap {text}: {node.get('bounds')}\n")
        tap_node(node)
    def scroll_to(text):
        for _ in range(20):
            root=tree()
            nodes=nodes_containing(root,text)
            if nodes:return nodes[-1]
            shell('input','swipe','500','1500','500','1000','1000')
        screen('scroll-failure');raise AssertionError('Cannot find '+text)
    package='io.github.styayur.lgxt_assistant_mobile'
    upgrade_incompatible=None
    if args.historical_apk:
        if 'Success' not in adb('install',args.historical_apk).decode():raise ValueError('Historical install failed')
        upgrade=subprocess.run(['adb','install','-r',args.apk],capture_output=True,timeout=90)
        if upgrade.returncode==0 or b'INSTALL_FAILED_UPDATE_INCOMPATIBLE' not in upgrade.stdout+upgrade.stderr:
            raise AssertionError('Historical signing incompatibility not established')
        upgrade_incompatible=True
        adb('uninstall',package)
    if 'Success' not in adb('install','-r',args.apk).decode():raise ValueError('APK installation failed')
    shell('logcat','-c')
    def launch():shell('am','start','-W','-n',package+'/.MainActivity')
    launch();root=wait_text('登录理工学堂');screen('login-native')
    edits=[node for node in root.iter('node') if node.get('class')=='android.widget.EditText']
    if len(edits)!=2:raise AssertionError('Expected two native editable login fields')
    for index,value in enumerate(['fixture-user','fixture-password']):
        # The Android keyboard changes the scroll viewport. Re-query bounds
        # for each field instead of reusing positions from before it opened.
        current=[node for node in tree().iter('node') if node.get('class')=='android.widget.EditText']
        tap_node(current[index]);shell('input','text',value)
        time.sleep(.5)
        shell('input','keyevent','4')
        time.sleep(.3)
    tap_text('登录理工学堂')
    passed=['install','first launch']
    if args.fixture:
        wait_text('刷新作业状态');tap_text('课程');tap_text('Fixture physics')
        tap_text('查看题目');screen('question-native-fixture')
        tap_text('提交成绩');wait_text('确认提交成绩');tap_text('取消')
        tap_text('提交成绩');tap_text('确认提交');wait_text('Fixture accepted')
        tap_node(scroll_to('查看原图 / 识别公式 / AI 分析'))
        wait_text('题目与解答');screen('document-native-fixture')
        # UIAutomator omits Flutter TextField hint/label text. Locate the note
        # field immediately before the visible model-settings section instead.
        anchor=scroll_to('模型设置')
        anchor_top=int(re.findall(r'\d+',anchor.get('bounds'))[1])
        fields=[node for node in tree().iter('node') if node.get('class')=='android.widget.EditText'
                and int(re.findall(r'\d+',node.get('bounds'))[3])<=anchor_top]
        if not fields:raise AssertionError('Solution note field not visible before model settings')
        tap_node(fields[-1])
        time.sleep(.3);screen('keyboard-native-fixture')
        shell('input','text','native-fixture-note');shell('input','keyevent','4')
        tap_node(scroll_to('保存学习材料'));wait_text('已保存到本机')
        screen('saved-native-fixture')
        tap_node(scroll_to('使用 AI 分析此题'));wait_text('视觉')
        screen('vision-rejected-native-fixture')
        passed+=['fixture course/assignment/question','submission cancel and confirm (no server)',
                 'note edit and save','unconfirmed vision rejected before provider request']
    else:
        wait_text('已阻止明文 HTTP');screen('http-blocked-native')
        tap_text('离线打开本地资料');wait_text('本地资料');screen('library-native')
        passed+=['HTTP blocked with dummy credentials','offline library']
        if args.backup_roundtrip:
            # Export through Android first so the picker indexes a real document.
            # Replace only that disposable emulator test file with synthetic notes.
            tap_text('导出备份');tap_text('SAVE');wait_text('本地资料')
            key='question.'+hashlib.sha256(json.dumps(['native-test','backup-test','1']).encode()).hexdigest()
            document={'schemaVersion':1,'courseId':'native-test','workId':'backup-test','questionId':'1',
                      'title':'Native acceptance — synthetic','courseName':'Synthetic offline test',
                      'workName':'Synthetic backup test','sourceText':'No real platform data',
                      'correctedMarkdown':'','solutionMarkdown':'native-fixture-note','originalImage':'','sources':[]}
            seed=out/'synthetic-note-backup.json'
            seed.write_text(json.dumps({'schemaVersion':1,'documents':{key:document}}),encoding='utf-8')
            device_backup='/sdcard/Download/LGXT-study-notes.json'
            adb('push',str(seed),device_backup)
            tap_text('导入备份 / 恢复');tap_text('LGXT-study-notes.json');tap_text('确认导入')
            tap_text('打开本地笔记');scroll_to('native-fixture-note')
            shell('rm',device_backup)
            passed.append('ordinary release APK imports a synthetic document through native picker')
    shell('input','keyevent','3');launch()
    wait_text('题目与解答' if args.fixture or args.backup_roundtrip else '本地资料')
    shell('am','force-stop',package);launch();wait_text('登录理工学堂');screen('restart-native')
    if args.fixture or args.backup_roundtrip:
        tap_text('离线打开本地资料');tap_text('打开本地笔记')
        scroll_to('native-fixture-note');screen('restored-native-fixture')
        passed.append('note survives process termination')
        shell('input','keyevent','4');wait_text('本地资料')
        screen('back-native-fixture')
        tap_text('导出备份');tap_text('SAVE');wait_text('本地资料')
        # Change the saved value after exporting, so import must actually
        # restore content rather than merely reopen an unchanged document.
        tap_text('打开本地笔记')
        tap_node(scroll_to('native-fixture-note'))
        shell('input','text','-after-export');shell('input','keyevent','4')
        tap_node(scroll_to('保存学习材料'));wait_text('已保存到本机')
        shell('input','keyevent','4');wait_text('本地资料')
        tap_text('导入备份 / 恢复');tap_text('LGXT-study-notes.json')
        wait_text('导入本地备份');tap_text('确认导入')
        wait_text('打开本地笔记');tap_text('打开本地笔记')
        restored=scroll_to('native-fixture-note')
        if restored.get('text')!='native-fixture-note':
            raise AssertionError('Native backup import did not restore exported note: '+str(restored.attrib))
        screen('backup-restored-native-fixture')
        passed+=['system back navigation','native file-picker backup export/import']
    log=shell('logcat','-d');(out/'logcat.txt').write_text(log,encoding='utf-8')
    if 'FATAL EXCEPTION' in log or 'Traceback (most recent call last)' in log:
        raise AssertionError('Native/Python crash in logcat')
    if args.fixture and 'LGXT_NATIVE_CHECKS=' not in log:raise AssertionError('Native decoder checks not reported')
    report={'package':package,'abi':shell('getprop','ro.product.cpu.abi').strip(),
            'android':shell('getprop','ro.build.version.release').strip(),
            'fixture':args.fixture,'syntheticDocuments':args.fixture or args.backup_roundtrip,'passed':passed+['background resume','force-stop restart'],
            'historicalUpgradeIncompatible':upgrade_incompatible,
            'not_covered':['real platform','paid provider','physical ARM64 device','signing continuity']}
    (out/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    sys.stdout.write(json.dumps(report,ensure_ascii=False)+'\n')


if __name__=='__main__':
    try:main()
    except Exception:
        output=Path(sys.argv[sys.argv.index('--output')+1] if '--output' in sys.argv else 'build/android/device')
        output.mkdir(parents=True,exist_ok=True)
        with (output/'failure-logcat.txt').open('wb') as target:
            subprocess.run(['adb','logcat','-d'],stdout=target,timeout=30,check=False)
        raise
