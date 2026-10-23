import React, { useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import { Node } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import Image from '@tiptap/extension-image';
import { TableKit } from '@tiptap/extension-table';
import { Markdown } from '@tiptap/markdown';
import katex from 'katex';
import { Button } from './ui';

function mathNode(block) {
  const name = block ? 'blockMath' : 'inlineMath';
  const delimiter = block ? '$$' : '$';
  return Node.create({
    name, group: block ? 'block' : 'inline', inline: !block, atom: true,
    addAttributes: () => ({ latex: { default: '', parseHTML: el => el.getAttribute('data-latex') || '' } }),
    parseHTML: () => [{ tag: `${block ? 'div' : 'span'}[data-math="${name}"]` }],
    renderHTML: ({ node }) => [block ? 'div' : 'span', { 'data-math': name, 'data-latex': node.attrs.latex }, node.attrs.latex],
    markdownTokenName: name,
    markdownTokenizer: {
      name, level: block ? 'block' : 'inline', start: src => src.indexOf(delimiter),
      tokenize(src) {
        const match = block ? /^\$\$\s*\n?([\s\S]+?)\n?\$\$(?:\n|$)/.exec(src) : /^\$([^$\n]+?)\$(?!\$)/.exec(src);
        if (match) return { type: name, raw: match[0], latex: match[1] };
      },
    },
    parseMarkdown: (token, helpers) => helpers.createNode(name, { latex: token.latex }),
    renderMarkdown: node => block ? `$$\n${node.attrs.latex}\n$$` : `$${node.attrs.latex}$`,
    addKeyboardShortcuts() {
      return { 'Mod-End': () => { this.editor.commands.focus('end'); return true; },
               'Mod-Home': () => { this.editor.commands.focus('start'); return true; } };
    },
    addNodeView() {
      return ({ node, editor, getPos }) => {
        const dom = document.createElement(block ? 'div' : 'span');
        dom.className = 'editable-math';
        dom.tabIndex = 0;
        dom.setAttribute('role', 'button');
        dom.setAttribute('aria-label', '编辑 LaTeX 公式');
        const draw = n => {
          dom.dataset.latex = n.attrs.latex;
          katex.render(n.attrs.latex, dom, { displayMode: block, throwOnError: false, trust: false, maxExpand: 1000, maxSize: 20 });
        };
        draw(node);
        const edit = () => {
          const latex = window.prompt('LaTeX 源码', dom.dataset.latex);
          if (latex !== null && latex.length <= 30000) editor.chain().focus().command(({ tr }) => {
            tr.setNodeMarkup(getPos(), undefined, { latex }); return true;
          }).run();
        };
        dom.onclick = edit;
        dom.onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); edit(); } };
        return { dom, update(n) { if (n.type.name !== name) return false; draw(n); return true; } };
      };
    },
  });
}
export const documentExtensions = () => [
  StarterKit.configure({ link: { openOnClick: false, protocols: ['https', 'http'], isAllowedUri: url => /^https?:\/\//i.test(url) } }),
  Image.configure({ allowBase64: true }), TableKit, Markdown, mathNode(true), mathNode(false),
];
export function safeImport(source) {
  if (source.length > 200000) throw Error('文档超过 200000 字符');
  // Imported remote images could track students or reach the local network.
  if (/!\[[^\]]*\]\(\s*(?!data:image\/(?:png|jpeg|webp);base64,)/i.test(source)) throw Error('导入图片须为本地 PNG、JPEG 或 WebP 数据；远程图片链接未导入。请保留原 Markdown。');
  return source.replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
export default function SolutionEditor({ value, onChange }) {
  const [source, setSource] = useState(() => {try {safeImport(value || '');return false;} catch{return true;}}), [draft, setDraft] = useState(value), [error, setError] = useState(() => {try {safeImport(value || '');return '';} catch(e){return e.message;}});
  let initial = '';
  try { initial = safeImport(value || ''); } catch { initial = (value || '').replace(/!\[[^\]]*\]\([^)]*\)/g, '[外部图片未导入]').replace(/</g, '&lt;'); }
  const editor = useEditor({ extensions: documentExtensions(), content: initial, contentType: 'markdown',
    onUpdate: ({ editor }) => onChange(editor.getMarkdown()),
    editorProps: { attributes: { 'aria-label': '题目解答编辑器', class: 'solution-editor' },
      transformPastedHTML: html => html.replace(/<img\b[^>]*>/gi, ''),
    },
  });
  if (!editor) return null;
  return <section className="document-editor">
    <div className="editor-toolbar" aria-label="文档格式">
      <Button onClick={() => editor.chain().focus().toggleBold().run()}>加粗</Button>
      <Button onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}>标题</Button>
      <Button onClick={() => editor.chain().focus().toggleBulletList().run()}>列表</Button>
      <Button onClick={() => editor.chain().focus().toggleCodeBlock().run()}>代码</Button>
      <Button onClick={() => editor.chain().focus().insertTable({ rows: 2, cols: 2, withHeaderRow: true }).run()}>表格</Button>
      <Button onClick={() => editor.chain().focus().insertContent({ type: 'inlineMath', attrs: { latex: 'x^2' } }).run()}>行内公式</Button>
      <Button onClick={() => editor.chain().focus().insertContent({ type: 'blockMath', attrs: { latex: '\\int_0^1 x^2\\,dx' } }).run()}>独立公式</Button>
      <label className="button">插入图片<input type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={async e => {
        const f=e.target.files[0]; if (!f) return;
        if (f.size > 2*1024*1024) {setError('图片超过 2 MB');return;}
        const data=await new Promise(resolve => {const r=new FileReader();r.onload=()=>resolve(r.result);r.readAsDataURL(f);});
        editor.chain().focus().setImage({src:data,alt:f.name}).run(); e.target.value='';
      }} /></label>
      <Button onClick={() => editor.chain().focus().undo().run()}>撤销</Button>
      <Button onClick={() => editor.chain().focus().redo().run()}>重做</Button>
      <Button onClick={() => { setDraft(editor.getMarkdown()); setSource(!source); }}>Markdown 源码</Button>
    </div>
    {source ? <><textarea aria-label="解答 Markdown 源码" rows={12} value={draft} onChange={e => setDraft(e.target.value)} />
      <Button onClick={() => { try { editor.commands.setContent(safeImport(draft), { contentType: 'markdown' }); onChange(editor.getMarkdown()); setError(''); setSource(false); } catch(e) {setError(e.message);} }}>转换并应用</Button>
      <p>转换支持标题、列表、代码、表格、图片和数学。原文在应用前保留；不支持任意 HTML。</p>
    </> : <EditorContent editor={editor} />}
    {error && <p role="alert" className="inline-error">{error}</p>}
  </section>;
}
