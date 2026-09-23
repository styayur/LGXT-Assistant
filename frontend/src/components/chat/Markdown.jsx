import React, { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeHighlight from "rehype-highlight";
import "katex/dist/katex.min.css";
import "highlight.js/styles/github-dark.css";
import { Copy } from "lucide-react";
import { Button } from "../ui";
function CodeBlock({ children }) {
  return (
    <div className="code-block">
      <div className="code-toolbar">
        <span>Code</span>
        <Button
          icon={Copy}
          label="复制代码"
          onClick={async (e) => {
            try {
              await navigator.clipboard.writeText(
                e.currentTarget.closest(".code-block").querySelector("pre")
                  .innerText,
              );
            } catch {
              window.dispatchEvent(
                new CustomEvent("lgxt-error", {
                  detail: "复制失败，请选择代码后按 Ctrl+C",
                }),
              );
            }
          }}
        />
      </div>
      <pre>{children}</pre>
    </div>
  );
}
export default memo(function Markdown({ text }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex, rehypeHighlight]}
        components={{
          pre: CodeBlock,
          table: ({ children }) => (
            <div className="table-scroll">
              <table>{children}</table>
            </div>
          ),
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer noopener">
              {children}
            </a>
          ),
          img: ({ src, alt }) => (
            <img loading="lazy" src={src} alt={alt || "消息图片"} />
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
});
