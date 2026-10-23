import React, { useEffect, useRef, useState } from 'react';
import { call } from '../lib/bridge';
import { Button, Skeleton, Modal } from './ui';
import Markdown from './chat/Markdown';
import SolutionEditor from './SolutionEditor';

export default function QuestionDocument({ course, work, question, files = [], toast }) {
  const [doc, setDoc] = useState(null), [busy, setBusy] = useState(false), [reply, setReply] = useState(''),
    [prompt, setPrompt] = useState('请逐步分析这道题，说明条件、公式和推导，并区分题目来源与模型推断。'),
    [includeImage, setIncludeImage] = useState(true), [crop, setCrop] = useState([0, 0, 100, 100]),
    [recognition, setRecognition] = useState(null), [editorVersion, setEditorVersion] = useState(0), [status, setStatus] = useState(''), [zoom, setZoom] = useState(false), [provenance, setProvenance] = useState({});
  const current = useRef(null), job = useRef(null), alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    const initial = { schemaVersion: 1, courseId: String(course.courseId), workId: String(work.workId), questionId: String(question.id),
      courseName: course.courseName, workName: work.workName, title: question.name || `题目 ${question.id}`,
      sourceText: question.text || question.name || '', recognizedText: '', latex: '', correctedMarkdown: question.text || '', solutionMarkdown: '',
      originalImage: '', answer: String(question.answer ?? ''), sources: [] };
    (async () => {
      try {
        const saved = await call('question_document', course.courseId, work.workId, question.id);
        const d = saved || initial;
        if (d.schemaVersion !== 1) throw Error('不支持的文档版本，请保留原文件后转换');
        if (!d.originalImage && question.imgurl && question.imgurl !== 'N/A') d.originalImage = await call('question_image', question.imgurl);
        if (alive.current) { current.current = d; setDoc(d); }
      } catch (e) { if (alive.current) { current.current = initial; setDoc(initial); toast(e.message, true); } }
    })();
    return () => { alive.current = false; if (job.current) call('stop_chat', job.current).catch(() => {}); };
  }, [course.courseId, work.workId, question.id]);
  function change(values) { const d = { ...current.current, ...values }; current.current = d; setDoc(d); setStatus('有未保存修改'); }
  async function save() { const d = await call('save_question_document', current.current); if (alive.current) {current.current = d; setDoc(d); setStatus('已保存到本机（保留上一版）');} return d; }
  async function selectedImage() {
    if (!doc.originalImage) return null;
    if (crop.join(',') === '0,0,100,100') return doc.originalImage;
    const [x,y,w,h] = crop;
    if (crop.some(n => !Number.isFinite(n)) || w <= 0 || h <= 0 || x < 0 || y < 0 || x+w > 100 || y+h > 100) throw Error('裁剪范围必须在原图内，宽高需大于零');
    const image = new Image(); image.src = doc.originalImage; await image.decode();
    const canvas = document.createElement('canvas'); canvas.width = Math.max(1, Math.round(image.width*w/100)); canvas.height = Math.max(1, Math.round(image.height*h/100));
    canvas.getContext('2d').drawImage(image, image.width*x/100, image.height*y/100, image.width*w/100, image.height*h/100, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/png');
  }
  async function run(recognize) {
    if (busy) return;
    setBusy(true); setReply(''); setStatus(recognize ? '正在识别…' : '正在分析…');
    try {
      const d = await save();
      const image = recognize || includeImage ? await selectedImage() : null;
      if (recognize && !image) throw Error('本题没有可识别图片');
      const id = await call('start_question_ai', d, prompt, image, recognize); job.current = id;
      let offset = 0, text = '';
      while (alive.current) {
        const r = await call('poll_job', id, offset); text += r.delta; offset = r.offset;
        if (!recognize) setReply(text);
        if (r.done) {
          if (r.error) throw Error(r.error);
          setProvenance({provider:r.provider || 'configured service',model:r.model || 'unknown',at:new Date().toISOString(),region:crop.join(',')});
          if (recognize) setRecognition(await call('parse_recognition', text));
          else change({discussion:[...(current.current.discussion || []).slice(-18), {role:'user',content:prompt.slice(0,30000)}, {role:'assistant',content:text.slice(0,30000)}]});
          setStatus(r.status); break;
        }
        await new Promise(resolve => setTimeout(resolve, 150));
      }
    } catch (e) { if (alive.current) {setStatus(e.message); toast(e.message, true);} }
    finally {job.current = null; if (alive.current) setBusy(false);}
  }
  if (!doc) return <Skeleton />;
  return <div className="assignment-studio">
    {zoom && <Modal title="原始题目图片" wide onClose={() => setZoom(false)}><img src={doc.originalImage} alt="原图放大" style={{maxWidth:"100%",maxHeight:"75dvh",objectFit:"contain",touchAction:"pinch-zoom"}} /></Modal>}
    <section className="question-document">
      <p className="source-provenance">原始来源：{course.courseName} / {work.workName} / 题目 {question.id}</p>
      {doc.originalImage ? <button className="original-image-button" onClick={() => setZoom(true)}><img className="question-image" src={doc.originalImage} alt="原始题目图片，点击放大" /></button> : <p>该题没有可用原图；可使用文字分析。</p>}
      <p className="muted">原始文字：{doc.sourceText || '平台未提供'}</p>
      <details><summary>识别整个原图或裁剪区域</summary><div className="crop-fields">
        {['左侧 %','顶部 %','宽度 %','高度 %'].map((label,i) => <label key={label}>{label}<input aria-label={label} type="number" min="0" max="100" value={crop[i]} onChange={e => setCrop(crop.map((n,j) => j===i ? Number(e.target.value) : n))} /></label>)}
      </div><p>原图始终保留。百分比以原图左上角为起点，默认选择整个图片。</p></details>
      <Button disabled={busy || !doc.originalImage} onClick={() => run(true)}>图片转 LaTeX</Button>
      {recognition && <section className="recognition-review"><h3>检查识别结果</h3><p>机器生成，可能有误；修改后应用到题面。</p>
        <label className="field">识别文字<textarea aria-label="识别文字" value={recognition.text} onChange={e => setRecognition({...recognition,text:e.target.value})} /></label>
        <label className="field">LaTeX 源码<textarea aria-label="LaTeX 源码" value={recognition.latex} onChange={e => setRecognition({...recognition,latex:e.target.value})} /></label>
        <Markdown text={`$$\n${recognition.latex}\n$$`} />
        <Button onClick={() => { change({ recognizedText: recognition.text, latex: recognition.latex, correctedMarkdown: `${recognition.text}\n\n$$\n${recognition.latex}\n$$`, recognition: provenance }); setRecognition(null); }}>应用校正结果</Button>
        <Button onClick={() => setRecognition(null)}>丢弃识别草稿</Button>
      </section>}
      <h3>题面与公式校正</h3>
      <label className="field">可编辑 Markdown / LaTeX<textarea aria-label="校正题面" rows={6} value={doc.correctedMarkdown} maxLength={200000} onChange={e => change({correctedMarkdown:e.target.value})} /></label>
      <Markdown text={doc.correctedMarkdown} />
      <h3>解答文档</h3>
      <SolutionEditor key={editorVersion} value={doc.solutionMarkdown} onChange={value => change({solutionMarkdown:value})} />
      <div className="row-actions"><Button onClick={() => save().catch(e => toast(e.message,true))}>保存题目文档</Button>
        {['md','docx','pdf'].map(format => <Button key={format} onClick={async () => { try {await save(); const r = await call('export_question_document', current.current, format); toast(`已导出：${r.path}`);} catch(e){toast(e.message,true);} }}>导出 {format}</Button>)}
      </div><p role="status">{status}</p>
    </section>
    <aside className="question-ai"><h3>围绕此题的 AI</h3>
      <p>点击分析或识别时，所选图片、题面、已有解答和勾选资料将发送给设置中的模型服务。输出可能有误。</p>
      <label><input type="checkbox" checked={includeImage} onChange={e => setIncludeImage(e.target.checked)} />包含题目图片（需视觉模型）</label>
      <details open><summary>选择支持资料</summary>{files.filter(f => typeof f.text === 'string').slice(0,8).map(f => <label className="source-choice" key={f.id}>
        <input type="checkbox" checked={doc.sources.some(s => s.name === f.name)} onChange={e => change({sources:e.target.checked ? [...doc.sources,{name:f.name,text:f.text}] : doc.sources.filter(s => s.name !== f.name)})} />{f.name}
      </label>)}{!files.some(f => typeof f.text === 'string') && <p>在工作区添加文本资料后可在此勾选。</p>}</details>
      <label className="field">分析与追问<textarea aria-label="围绕此题提问" rows={5} value={prompt} onChange={e => setPrompt(e.target.value)} /></label>
      <Button className="primary" disabled={busy || !prompt.trim()} onClick={() => run(false)}>使用 AI 分析此题</Button>
      {busy && <Button onClick={() => call('stop_chat', job.current)}>停止生成</Button>}
      {reply && <><p className="source-provenance">模型生成 · 题目 {question.id} · 来源仅为上方题目与勾选资料</p><Markdown text={reply} />
        <Button onClick={() => {change({solutionMarkdown:current.current.solutionMarkdown + '\n\n' + reply}); setEditorVersion(v => v+1);}}>将回复加入解答</Button></>}
    </aside>
  </div>;
}
