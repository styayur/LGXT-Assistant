export const defaults = {
  theme: "dark",
  language: "zh",
  startup: "last",
  reduceMotion: false,
  provider: "OpenAI",
  endpoint: "https://api.openai.com/v1",
  model: "",
  temperature: 0.7,
  contextMessages: 40,
  maxTokens: 4096,
  storeConversations: true,
  memoryEnabled: false,
  memory: "",
  debug: false,
  profiles: {},
};
export const providers = {
  OpenAI: {
    endpoint: "https://api.openai.com/v1",
    hint: "输入你的 GPT 模型 ID",
  },
  Claude: {
    endpoint: "https://api.anthropic.com/v1",
    hint: "输入你的 Claude 模型 ID",
  },
  Gemini: {
    endpoint: "https://generativelanguage.googleapis.com/v1beta/openai",
    hint: "输入你的 Gemini 模型 ID",
  },
  Local: {
    endpoint: "http://localhost:11434/v1",
    hint: "输入已安装的本地模型 ID",
  },
};
export function switchProvider(settings, provider) {
  const profiles = {
    ...settings.profiles,
    [settings.provider]: { endpoint: settings.endpoint, model: settings.model },
  };
  return {
    ...settings,
    provider,
    profiles,
    ...(profiles[provider] || {
      endpoint: providers[provider].endpoint,
      model: "",
    }),
  };
}
const read = (key, fallback) =>
  JSON.parse(
    localStorage.getItem(`lgxt.preview.${key}`) || JSON.stringify(fallback),
  );
const write = (key, value) =>
  localStorage.setItem(`lgxt.preview.${key}`, JSON.stringify(value));
export const isDesktop = () => Boolean(window.pywebview?.api);
export const desktopExpected = () =>
  document.documentElement.dataset.desktop === "true";
export function withTimeout(promise, ms, message) {
  let timer;
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      timer = setTimeout(() => reject(Error(message)), ms);
    }),
  ]).finally(() => clearTimeout(timer));
}
export function waitForBridge(ms = 12000) {
  if (isDesktop() || !desktopExpected()) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      clearTimeout(timer);
      window.removeEventListener("pywebviewready", ready);
    };
    const ready = () => {
      if (isDesktop()) {
        cleanup();
        resolve();
      }
    };
    const timer = setTimeout(() => {
      cleanup();
      reject(
        Error(
          "桌面连接未就绪。请关闭窗口后重新打开完整版程序，或安装 / 更新 Microsoft WebView2 运行时。",
        ),
      );
    }, ms);
    window.addEventListener("pywebviewready", ready);
    ready();
  });
}
export async function call(method, ...args) {
  if (isDesktop()) return window.pywebview.api[method](...args);
  if (desktopExpected()) throw Error("桌面连接尚未就绪，请重新打开程序。");
  // Browser development mode supports local editing, never simulated server responses.
  switch (method) {
    case "bootstrap":
      return {
        settings: { ...defaults, ...read("settings", {}) },
        hasKey: false,
        conversations: read("index", []),
        prompts: read("prompts", []),
        workspace: read("workspace", { files: [], task: "" }),
        username: "",
        savedUsername: "",
        export: {
          export_path: "",
          export_word: true,
          export_pdf: false,
          export_word_include_answers: true,
          export_pdf_include_answers: true,
        },
      };
    case "save_settings":
      if (args[1]) throw Error("浏览器预览不保存密钥，请使用桌面应用");
      args[0] = {
        ...args[0],
        profiles: {
          ...args[0].profiles,
          [args[0].provider]: {
            endpoint: args[0].endpoint,
            model: args[0].model,
          },
        },
      };
      write("settings", args[0]);
      return { settings: args[0], hasKey: false };
    case "save_conversation": {
      if (!read("settings", defaults).storeConversations) return false;
      const c = args[0];
      write(c.id, c);
      write("index", [
        { id: c.id, title: c.title, updated: c.updated },
        ...read("index", []).filter((x) => x.id !== c.id),
      ]);
      return true;
    }
    case "conversation":
      return read(args[0], null);
    case "delete_conversation":
      localStorage.removeItem(`lgxt.preview.${args[0]}`);
      write(
        "index",
        read("index", []).filter((x) => x.id !== args[0]),
      );
      return;
    case "save_prompts":
      write("prompts", args[0]);
      return;
    case "save_workspace":
      write("workspace", args[0]);
      return;
    case "export_chat": {
      const url = URL.createObjectURL(
        new Blob([args[1]], { type: "text/markdown" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = args[0] + ".md";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      return true;
    }
    default:
      throw Error("此操作需要桌面连接。请运行 python default.pyw");
  }
}
export const uid = () => {
  if (crypto.randomUUID) return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  const h = [...bytes].map((n) => n.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
};
export const newConversation = () => ({
  id: uid(),
  title: "新会话",
  updated: Date.now(),
  messages: [],
});
export async function browserFiles(files) {
  const result = [];
  for (const file of [...files].slice(0, 8)) {
    if (file.size > 2 * 1024 * 1024) throw Error(`${file.name} 超过 2 MB`);
    const item = { id: uid(), name: file.name, size: file.size };
    if (/^image\/(png|jpeg|webp)$/.test(file.type))
      item.data = await new Promise((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => resolve(r.result);
        r.onerror = reject;
        r.readAsDataURL(file);
      });
    else item.text = (await file.text()).slice(0, 60000);
    result.push(item);
  }
  return result;
}
