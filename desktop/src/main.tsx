import React, { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { EditorView } from "@codemirror/view";
import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { tags } from "@lezer/highlight";
import {
  Area,
  Line,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Activity,
  ArrowUpRight,
  BookOpen,
  Braces,
  CheckCircle2,
  ChevronRight,
  Code2,
  Cpu,
  Database,
  FileCode2,
  FolderOpen,
  FlaskConical,
  History,
  Layers3,
  LoaderCircle,
  Moon,
  Play,
  Plus,
  RefreshCw,
  Save,
  Settings2,
  ShieldCheck,
  Square,
  Sun,
  X,
  Zap,
} from "lucide-react";
import { command, rpc } from "./api";
import "./styles.css";
import { version as appVersion } from "../package.json";

type Catalog = {
  root: string;
  strategies: string[];
  factors: string[];
  configs: string[];
  data: { path: string; bytes: number }[];
};
type Doc = { text: string; saved: string; hash: string | null };
const short = (s: string) => s.split("/").pop() || s;
const money = (n: any) =>
  Number.isFinite(Number(n)) && n !== null
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(Number(n))
    : "—";
const percent = (n: any) =>
  n === null || n === undefined ? "—" : `${(Number(n) * 100).toFixed(2)}%`;
const number = (n: any) =>
  n === null || n === undefined ? "—" : Number(n).toFixed(2);
const defaultRoot = localStorage.getItem("quantlab.workspace") || "";
const icons = {
  studio: Code2,
  history: History,
  data: Database,
  settings: Settings2,
};
const themeEditor = EditorView.theme({
  "&": {
    backgroundColor: "transparent",
    color: "var(--text)",
    fontSize: "13px",
  },
  ".cm-content": {
    fontFamily: "var(--mono)",
    padding: "20px 0",
    caretColor: "var(--cyan)",
  },
  ".cm-gutters": {
    backgroundColor: "transparent",
    color: "var(--muted)",
    border: "none",
  },
  ".cm-activeLineGutter": { backgroundColor: "var(--selected)" },
  ".cm-activeLine": { backgroundColor: "var(--selected)" },
  ".cm-selectionBackground, &.cm-focused .cm-selectionBackground": {
    backgroundColor: "var(--selection)",
  },
  ".cm-scroller": { overflow: "auto" },
  "&.cm-focused": { outline: "none" },
  ".cm-cursor": { borderLeftColor: "var(--cyan)" },
  ".cm-line": { padding: "0 16px" },
  ".cm-gutterElement": { padding: "0 12px" },
});
const syntax = syntaxHighlighting(
  HighlightStyle.define([
    { tag: [tags.keyword, tags.operatorKeyword], color: "var(--purple)" },
    { tag: [tags.string, tags.special(tags.string)], color: "var(--green)" },
    { tag: tags.comment, color: "var(--muted)", fontStyle: "italic" },
    {
      tag: [
        tags.function(tags.variableName),
        tags.definition(tags.variableName),
      ],
      color: "var(--cyan)",
    },
    { tag: [tags.number, tags.bool], color: "var(--orange)" },
    { tag: tags.className, color: "var(--purple)" },
  ]),
);

function App() {
  const [theme, setTheme] = useState(
    localStorage.getItem("quantlab.theme") || "dark",
  );
  const [root, setRoot] = useState(defaultRoot),
    [rootInput, setRootInput] = useState(defaultRoot);
  const [catalog, setCatalog] = useState<Catalog | null>(null),
    [config, setConfig] = useState<any>(null),
    [configPath, setConfigPath] = useState("");
  const [docs, setDocs] = useState<Record<string, Doc>>({}),
    [activeFile, setActiveFile] = useState(""),
    [factor, setFactor] = useState("");
  const [page, setPage] = useState<"studio" | "history" | "data" | "settings">(
    "studio",
  );
  const [history, setHistory] = useState<any[]>([]),
    [result, setResult] = useState<any>(null),
    [selectedRun, setSelectedRun] = useState("");
  const [busy, setBusy] = useState(false),
    [job, setJob] = useState<string | null>(null),
    [jobState, setJobState] = useState("idle"),
    [log, setLog] = useState("");
  const [notice, setNotice] = useState<{
      message: string;
      error: boolean;
    } | null>(null),
    [pane, setPane] = useState<"equity" | "fills" | "logs">("equity");
  const [report, setReport] = useState<string | null>(null),
    [newFile, setNewFile] = useState<"strategies" | "factors" | null>(null),
    [newName, setNewName] = useState("");
  const [reloadPath, setReloadPath] = useState<string | null>(null);
  const [params, setParams] = useState("{}"),
    [advanced, setAdvanced] = useState(false);
  const docRef = useRef(docs);
  docRef.current = docs;
  const editorRef = useRef<EditorView | null>(null);
  const running = !!job,
    dirty = Object.values(docs).some((d) => d.text !== d.saved);
  const notify = (message: string, error = false) =>
    setNotice({ message, error });
  const perform = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      notify(String(e instanceof Error ? e.message : e), true);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("quantlab.theme", theme);
  }, [theme]);
  useEffect(() => {
    const h = (e: BeforeUnloadEvent) => {
      if (dirty || running) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [dirty, running]);
  useEffect(() => {
    (async () => {
      let path = root;
      if (!path) path = await command<string>("default_workspace");
      setRoot(path);
      setRootInput(path);
      await connect(path);
    })().catch((e) => {
      notify(String(e), true);
      setPage("settings");
    });
  }, []);
  useEffect(() => {
    if (!report && !newFile && !reloadPath) return;
    const previous = document.activeElement as HTMLElement | null;
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setReport(null);
        setNewFile(null);
        setReloadPath(null);
      }
      if (e.key === "Tab") {
        const modal = document.querySelector('[role="dialog"]');
        const focusable = Array.from(
          modal?.querySelectorAll<HTMLElement>(
            "button:not(:disabled),input,iframe,textarea,select",
          ) || [],
        );
        const first = focusable[0],
          last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, [report, newFile, reloadPath]);
  async function openFile(path: string) {
    if (!path) return;
    if (!docRef.current[path]) {
      const d = await rpc(root || rootInput, "read", { path });
      setDocs((prev) => ({ ...prev, [path]: { ...d, saved: d.text } }));
    }
    setActiveFile(path);
  }
  async function loadConfig(path: string, workspace = root) {
    const c = await rpc(workspace, "config", { path });
    setConfig(c);
    setConfigPath(path);
    setParams(JSON.stringify(c.strategy.params, null, 2));
    const files = [
      c.strategy.path,
      ...Object.values(c.strategy.factor_paths),
    ] as string[];
    const loaded: Record<string, Doc> = {};
    for (const f of files) {
      if (!docRef.current[f]) {
        try {
          const d = await rpc(workspace, "read", { path: f });
          loaded[f] = { ...d, saved: d.text };
        } catch {
          /* Missing implementations remain visible as validation errors. */
        }
      }
    }
    setDocs((prev) => ({ ...prev, ...loaded }));
    setActiveFile(c.strategy.path);
    setFactor(files[1] || "");
  }
  async function connect(path: string) {
    const cat = await rpc(path, "catalog");
    setCatalog(cat);
    setRoot(path);
    setRootInput(path);
    localStorage.setItem("quantlab.workspace", path);
    const runs = await rpc(path, "history");
    setHistory(runs);
    const preferred =
      cat.configs.find((p: string) =>
        p.includes("aapl_weekly_relative_reversal"),
      ) || cat.configs[0];
    if (preferred) await loadConfig(preferred, path);
    const recent =
      runs.find(
        (r: any) =>
          r.status === "complete" &&
          r.id.includes("aapl_weekly_relative_reversal"),
      ) || runs.find((r: any) => r.status === "complete");
    if (recent) {
      setResult(await rpc(path, "result", { id: recent.id }));
      setSelectedRun(recent.id);
    }
  }
  async function refresh() {
    setCatalog(await rpc(root, "catalog"));
    setHistory(await rpc(root, "history"));
    notify("目录与回测记录已刷新；编辑中的内容保持不变。");
  }
  async function saveAll() {
    for (const [path, doc] of Object.entries(docRef.current)) {
      if (doc.text !== doc.saved) {
        const saved = await rpc(root, "save", {
          path,
          text: doc.text,
          hash: doc.hash,
        });
        setDocs((prev) => ({
          ...prev,
          [path]: { ...doc, saved: doc.text, hash: saved.hash },
        }));
      }
    }
  }
  function runConfig() {
    if (!config) throw new Error("请先选择回测配置");
    const parsed = JSON.parse(params);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object")
      throw new Error("策略参数必须为 JSON 对象");
    return { ...config, strategy: { ...config.strategy, params: parsed } };
  }
  async function validate() {
    await saveAll();
    const r = await rpc(root, "validate", { config: runConfig() });
    notify(r.message);
  }
  async function run() {
    await saveAll();
    const c = runConfig();
    await rpc(root, "validate", { config: c });
    const task = await command<any>("start_run", { root, config: c });
    setJob(task.id);
    setJobState("running");
    setLog("正在准备冻结快照并启动回测…");
    setPane("logs");
    notify("回测已启动，使用本次保存的代码与参数。");
  }
  useEffect(() => {
    if (!job) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const s = await command<any>("job_status", { id: job });
        if (disposed) return;
        setLog(s.log || "正在初始化 Python 引擎…");
        if (s.status !== "running") {
          setJobState(s.status);
          if (s.status === "complete") {
            const r = await rpc(root, "result", { id: s.run_id });
            if (disposed) return;
            setResult(r);
            setSelectedRun(s.run_id);
            setHistory(await rpc(root, "history"));
            setPane("equity");
            notify("回测完成，结果与输入快照已归档。");
          } else
            notify(
              s.status === "cancelled"
                ? "回测已取消；未完成的输出不作为有效结果。"
                : s.error || "回测失败，请查看日志。",
              s.status !== "cancelled",
            );
          setJob(null);
          return;
        }
        timer = setTimeout(poll, 900);
      } catch (e) {
        if (!disposed) {
          notify(String(e), true);
          timer = setTimeout(poll, 2000);
        }
      }
    };
    poll();
    return () => {
      disposed = true;
      clearTimeout(timer);
    };
  }, [job, root]);
  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        if (!busy && !running)
          perform(async () => {
            await saveAll();
            notify("所有修改已保存");
          });
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [busy, running]);
  function update(section: string, key: string, value: any) {
    setConfig((c: any) => ({
      ...c,
      [section]: { ...c[section], [key]: value },
    }));
  }
  async function chooseStrategy(path: string) {
    const match = catalog?.configs.find((p) =>
      short(p).startsWith(short(path).replace(".py", "")),
    );
    if (match) await loadConfig(match);
    else {
      update("strategy", "path", path);
      notify("已更换策略；请核对参数、股票和因子依赖后校验。");
      await openFile(path);
    }
  }
  async function chooseRun(id: string) {
    const r = await rpc(root, "result", { id });
    setResult(r);
    setSelectedRun(id);
    setPage("studio");
    setPane("equity");
  }
  async function createFile() {
    if (!newFile || !/^[_a-zA-Z]\w*\.py$/.test(newName))
      throw new Error("请输入合法 Python 文件名，例如 my_strategy.py");
    const path = `${newFile}/${newName}`;
    const text =
      newFile === "factors"
        ? '"""在这里定义你的因子计算。"""\n\ndef compute(data):\n    raise NotImplementedError("请实现因子计算")\n'
        : (await rpc(root, "read", { path: "strategies/_template.py" })).text;
    const saved = await rpc(root, "save", { path, text, hash: null });
    setDocs((prev) => ({
      ...prev,
      [path]: { text, saved: text, hash: saved.hash },
    }));
    setActiveFile(path);
    if (newFile === "factors") setFactor(path);
    setNewFile(null);
    setNewName("");
    await refresh();
    notify("文件已创建；实现并校验后再绑定回测。");
  }
  const metrics = result?.summary?.metrics || {};
  const benchmarkMap = new Map(
    (result?.benchmark || []).map((r: any) => [r.date, r]),
  );
  const chart = (result?.equity || []).map((r: any) => ({
    date: r.date,
    equity: Number(r.equity),
    benchmark:
      Number(
        (benchmarkMap.get(r.date) as any)?.equity ??
          (benchmarkMap.get(r.date) as any)?.benchmark_equity,
      ) || undefined,
  }));
  const first = chart[0]?.equity || 1;
  const chartData = chart.map((r: any) => ({
    ...r,
    equity: (r.equity / first - 1) * 100,
    benchmark: r.benchmark
      ? (r.benchmark / (chart.find((x: any) => x.benchmark)?.benchmark || 1) -
          1) *
        100
      : undefined,
  }));
  const activeDoc = docs[activeFile];
  const bindName = factor ? "factors." + short(factor).replace(".py", "") : "";
  const bound =
    config && Object.values(config.strategy.factor_paths).includes(factor);
  const labels = {
    studio: "研究工作台",
    history: "回测记录",
    data: "数据目录",
    settings: "工作区设置",
  };
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-symbol">
            <Activity size={26} />
          </span>
          <span>
            QUANT<span className="accent">LAB</span>
            <small>RESEARCH TERMINAL</small>
          </span>
        </div>
        <div className="workspace-card">
          <span className="live-dot" />
          <div>
            本地研究空间
            <small>
              {catalog ? "LOCAL ENGINE CONNECTED" : "等待连接工作区"}
            </small>
          </div>
          <ChevronRight size={14} />
        </div>
        <p className="eyebrow nav-heading">WORKSPACE</p>
        <nav>
          {(Object.keys(icons) as (keyof typeof icons)[]).map((key) => {
            const Icon = icons[key];
            return (
              <button
                key={key}
                aria-label={labels[key]}
                title={labels[key]}
                className={page === key ? "nav-item selected" : "nav-item"}
                onClick={() => setPage(key)}
              >
                <Icon size={19} />
                <span>{labels[key]}</span>
                {key === "studio" && <span className="nav-shortcut">⌘</span>}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="engine-card">
            <Cpu size={19} />
            <strong>
              QuantLab Engine<small>Python · 日线回测</small>
            </strong>
            <span className={catalog ? "live-dot" : "offline-dot"} />
          </div>
          <div className="local-note">
            <ShieldCheck size={14} /> 数据与代码存储于本机
          </div>
          <div className="theme-switch" aria-label="界面主题">
            <button
              aria-pressed={theme === "dark"}
              className={theme === "dark" ? "active" : ""}
              onClick={() => setTheme("dark")}
            >
              <Moon size={15} /> 深色
            </button>
            <button
              aria-pressed={theme === "light"}
              className={theme === "light" ? "active" : ""}
              onClick={() => setTheme("light")}
            >
              <Sun size={15} /> 浅色
            </button>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumbs">
            工作空间 <ChevronRight size={13} />
            <span>{labels[page]}</span>
          </div>
          <div className="topbar-right">
            <span className="version">DESKTOP / {appVersion}</span>
            <span className="divider" />
            <span className="status">
              <span className={running ? "live-dot pulse" : "live-dot"} />
              {running ? "引擎运行中" : "本地运行"}
            </span>
            <button
              className="icon-button"
              title="刷新目录与历史"
              aria-label="刷新目录与历史"
              disabled={busy}
              onClick={() => perform(refresh)}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </header>
        <div className="main-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">
                {page === "studio"
                  ? "BUILD. TEST. UNDERSTAND."
                  : "QUANTITATIVE RESEARCH"}
              </p>
              <h1>
                {labels[page]}
                <span className="heading-dot">.</span>
              </h1>
              <p className="subtitle">
                {page === "studio"
                  ? "让每一个交易想法，接受数据的检验。"
                  : page === "history"
                    ? "每一次实验，都有迹可循。"
                    : page === "data"
                      ? "查看本地行情文件，选择可复现的数据来源。"
                      : "连接你的项目，让研究始终留在本地。"}
              </p>
            </div>
            {page === "studio" && (
              <div className="heading-actions">
                <button
                  className="secondary"
                  disabled={busy || running || !config}
                  onClick={() => perform(validate)}
                >
                  <ShieldCheck size={16} /> 校验策略
                </button>
                <button
                  className="primary"
                  disabled={busy || !config}
                  onClick={() =>
                    perform(
                      running
                        ? async () => {
                            await command("cancel_run", { id: job });
                          }
                        : run,
                    )
                  }
                >
                  {busy ? (
                    <LoaderCircle className="spin" size={17} />
                  ) : running ? (
                    <Square size={15} />
                  ) : (
                    <Play size={16} />
                  )}{" "}
                  {running ? "取消回测" : "运行回测"}
                  <kbd>▶</kbd>
                </button>
              </div>
            )}
          </div>
          {notice && (
            <div
              role={notice.error ? "alert" : "status"}
              className={`notice ${notice.error ? "error" : ""}`}
            >
              <span>{notice.error ? "!" : <CheckCircle2 size={16} />}</span>
              <p>{notice.message}</p>
              <button
                aria-label="关闭消息"
                className="icon-button"
                onClick={() => setNotice(null)}
              >
                <X size={14} />
              </button>
            </div>
          )}
          {page === "studio" && (
            <>
              <div className="studio-grid">
                <section className="panel editor-panel">
                  <div className="section-header">
                    <div>
                      <span className="section-icon">
                        <Braces size={17} />
                      </span>
                      <h2>策略实验室</h2>
                      <span className="micro-badge">PYTHON</span>
                    </div>
                    <button
                      className="text-button"
                      disabled={busy || running}
                      onClick={() => {
                        setNewFile("strategies");
                        setNewName("");
                      }}
                    >
                      <Plus size={14} /> 新建
                    </button>
                  </div>
                  <div className="selectors">
                    <label>
                      交易策略
                      <select
                        aria-label="交易策略"
                        disabled={busy || running}
                        value={config?.strategy.path || ""}
                        onChange={(e) =>
                          perform(() => chooseStrategy(e.target.value))
                        }
                      >
                        <option value="" disabled>
                          选择策略文件
                        </option>
                        {catalog?.strategies.map((p) => (
                          <option key={p} value={p}>
                            {short(p)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      因子文件<span className="label-hint">编辑 / 绑定</span>
                      <div className="factor-select">
                        <select
                          aria-label="因子文件"
                          disabled={busy || running}
                          value={factor}
                          onChange={(e) => {
                            setFactor(e.target.value);
                            perform(() => openFile(e.target.value));
                          }}
                        >
                          <option value="">不选择因子</option>
                          {catalog?.factors.map((p) => (
                            <option key={p} value={p}>
                              {short(p)}
                            </option>
                          ))}
                        </select>
                        <button
                          className="icon-button"
                          aria-label="新建因子文件"
                          disabled={running || busy}
                          onClick={() => {
                            setNewFile("factors");
                            setNewName("");
                          }}
                        >
                          <Plus size={16} />
                        </button>
                      </div>
                    </label>
                  </div>
                  {factor && config && (
                    <div className="dependency">
                      <Layers3 size={13} />
                      <span>
                        {bound ? "已绑定依赖" : "仅编辑，尚未绑定"} · {bindName}
                      </span>
                      <button
                        disabled={running || busy}
                        className="text-button"
                        onClick={() => {
                          const bindings = { ...config.strategy.factor_paths };
                          if (bound) {
                            for (const k in bindings)
                              if (bindings[k] === factor) delete bindings[k];
                          } else bindings[bindName] = factor;
                          update("strategy", "factor_paths", bindings);
                        }}
                      >
                        {bound ? "移除依赖" : "+ 绑定到策略"}
                      </button>
                    </div>
                  )}
                  <div className="editor-tabs">
                    <div role="tablist" aria-label="打开的代码文件">
                      {Object.keys(docs).map((p) => (
                        <button
                          role="tab"
                          aria-selected={activeFile === p}
                          key={p}
                          className={activeFile === p ? "active" : ""}
                          onClick={() => setActiveFile(p)}
                        >
                          <FileCode2 size={14} />
                          <span>{short(p)}</span>
                          {docs[p].text !== docs[p].saved && (
                            <span className="unsaved-dot" />
                          )}
                        </button>
                      ))}
                    </div>
                    <button
                      className="icon-button"
                      title="重新读取磁盘文件"
                      aria-label="重新读取磁盘文件"
                      disabled={busy || running || !activeDoc}
                      onClick={() => setReloadPath(activeFile)}
                    >
                      <RefreshCw size={15} />
                    </button>
                    <button
                      className="icon-button"
                      title="保存所有修改 ⌘S"
                      aria-label="保存所有修改"
                      disabled={busy || running || !dirty}
                      onClick={() =>
                        perform(async () => {
                          await saveAll();
                          notify("所有修改已保存");
                        })
                      }
                    >
                      <Save size={16} />
                    </button>
                  </div>
                  <div className="code-area">
                    {activeDoc ? (
                      <CodeMirror
                        value={activeDoc.text}
                        theme="none"
                        height="355px"
                        editable={!busy && !running}
                        extensions={[python(), themeEditor, syntax]}
                        basicSetup={{
                          lineNumbers: true,
                          foldGutter: true,
                          highlightActiveLine: true,
                          autocompletion: true,
                        }}
                        onCreateEditor={(v) => (editorRef.current = v)}
                        onChange={(text) =>
                          setDocs((prev) => ({
                            ...prev,
                            [activeFile]: { ...prev[activeFile], text },
                          }))
                        }
                      />
                    ) : (
                      <div className="empty">
                        <FileCode2 size={32} />
                        <p>选择一个本地 Python 文件开始编辑</p>
                      </div>
                    )}
                  </div>
                  <footer className="editor-footer">
                    <span>
                      <span className={dirty ? "unsaved-dot" : "live-dot"} />
                      {dirty ? "有未保存的修改" : "文件已保存"}{" "}
                      {running && " · 回测期间只读"}
                    </span>
                    <span>
                      Python 3 · UTF-8{" "}
                      <span className="shortcut">⌘ S 保存</span>
                    </span>
                  </footer>
                </section>
                <section className="panel config-panel">
                  <div className="section-header">
                    <div>
                      <Settings2 size={17} />
                      <h2>回测配置</h2>
                    </div>
                    <span className="micro-badge neutral">LOCAL</span>
                  </div>
                  {config ? (
                    <fieldset
                      disabled={busy || running}
                      className="config-fields"
                    >
                      <label>
                        配置预设
                        <select
                          aria-label="配置预设"
                          value={configPath}
                          onChange={(e) =>
                            perform(() => loadConfig(e.target.value))
                          }
                        >
                          {catalog?.configs.map((p) => (
                            <option key={p} value={p}>
                              {short(p)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <div className="form-row">
                        <label>
                          开始日期
                          <input
                            aria-label="开始日期"
                            type="date"
                            value={config.backtest.start_date}
                            onChange={(e) =>
                              update("backtest", "start_date", e.target.value)
                            }
                          />
                        </label>
                        <label>
                          结束日期
                          <input
                            aria-label="结束日期"
                            type="date"
                            value={config.backtest.end_date}
                            onChange={(e) =>
                              update("backtest", "end_date", e.target.value)
                            }
                          />
                        </label>
                      </div>
                      <label>
                        初始资金 <span className="label-hint">USD</span>
                        <input
                          aria-label="初始资金"
                          type="number"
                          min="1"
                          value={config.backtest.initial_cash}
                          onChange={(e) =>
                            update(
                              "backtest",
                              "initial_cash",
                              Number(e.target.value),
                            )
                          }
                        />
                      </label>
                      <div className="form-row">
                        <label>
                          股票池
                          <input
                            aria-label="股票池"
                            value={config.universe.symbols.join(", ")}
                            onChange={(e) =>
                              update(
                                "universe",
                                "symbols",
                                e.target.value
                                  .split(",")
                                  .map((s) => s.trim().toUpperCase()),
                              )
                            }
                          />
                        </label>
                        <label>
                          基准
                          <input
                            aria-label="基准"
                            value={config.data.benchmark}
                            onChange={(e) =>
                              update(
                                "data",
                                "benchmark",
                                e.target.value.toUpperCase(),
                              )
                            }
                          />
                        </label>
                      </div>
                      <label>
                        行情数据
                        <select
                          aria-label="行情数据"
                          value={config.data.path}
                          onChange={(e) =>
                            setConfig({
                              ...config,
                              data: {
                                ...config.data,
                                path: e.target.value,
                                provider: e.target.value.endsWith(".csv")
                                  ? "csv_local"
                                  : "parquet_local",
                                source:
                                  "User-selected local data; provenance unverified",
                              },
                            })
                          }
                        >
                          {catalog?.data.map((d) => (
                            <option key={d.path} value={d.path}>
                              {short(d.path)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <div className="execution-note">
                        <Zap size={15} />
                        <span>收盘决策 · 下一交易日开盘执行</span>
                      </div>
                      <button
                        type="button"
                        className="advanced-toggle"
                        aria-expanded={advanced}
                        onClick={() => setAdvanced(!advanced)}
                      >
                        策略参数与交易成本{" "}
                        <ChevronRight
                          size={14}
                          className={advanced ? "rotate" : ""}
                        />
                      </button>
                      {advanced && (
                        <div className="advanced">
                          <label>
                            策略参数（JSON）
                            <textarea
                              aria-label="策略参数"
                              rows={7}
                              value={params}
                              onChange={(e) => setParams(e.target.value)}
                            />
                          </label>
                          <label>
                            仓位计算
                            <select
                              value={config.execution.sizing}
                              onChange={(e) =>
                                update("execution", "sizing", e.target.value)
                              }
                            >
                              <option value="target_weights">目标权重</option>
                              <option value="decision_relative">
                                保持买入现金 / 卖出股数比例
                              </option>
                            </select>
                          </label>
                          <label>
                            手续费模型
                            <select
                              value={config.commission.model}
                              onChange={(e) =>
                                update("commission", "model", e.target.value)
                              }
                            >
                              <option value="per_share">按股收费</option>
                              <option value="bps">成交额基点</option>
                              <option value="zero">零手续费</option>
                            </select>
                          </label>
                          <div className="form-row">
                            <label>
                              每股费用
                              <input
                                type="number"
                                min="0"
                                step="0.001"
                                value={config.commission.per_share}
                                onChange={(e) =>
                                  update(
                                    "commission",
                                    "per_share",
                                    Number(e.target.value),
                                  )
                                }
                              />
                            </label>
                            <label>
                              最低费用
                              <input
                                type="number"
                                min="0"
                                value={config.commission.minimum}
                                onChange={(e) =>
                                  update(
                                    "commission",
                                    "minimum",
                                    Number(e.target.value),
                                  )
                                }
                              />
                            </label>
                          </div>
                          {config.commission.model === "bps" && (
                            <label>
                              手续费（bps）
                              <input
                                type="number"
                                min="0"
                                value={config.commission.bps}
                                onChange={(e) =>
                                  update(
                                    "commission",
                                    "bps",
                                    Number(e.target.value),
                                  )
                                }
                              />
                            </label>
                          )}
                          <label>
                            滑点（bps）
                            <input
                              type="number"
                              min="0"
                              value={
                                config.slippage.model === "zero"
                                  ? 0
                                  : config.slippage.bps
                              }
                              onChange={(e) =>
                                setConfig({
                                  ...config,
                                  slippage: {
                                    model: "bps",
                                    bps: Number(e.target.value),
                                  },
                                })
                              }
                            />
                          </label>
                        </div>
                      )}
                      <div className="config-footnote">
                        <ShieldCheck size={14} /> 保存代码后校验，运行时冻结快照
                      </div>
                    </fieldset>
                  ) : (
                    <div className="empty">
                      <p>请先连接本地工作区</p>
                    </div>
                  )}
                </section>
              </div>
              <section className="results">
                <div className="results-heading">
                  <div>
                    <span className="eyebrow">EXPERIMENT OUTPUT</span>
                    <h2>
                      回测洞察{" "}
                      <span className="micro-badge">
                        {result ? "真实历史结果" : "等待首次回测"}
                      </span>
                    </h2>
                  </div>
                  <button
                    className="text-button"
                    disabled={!result || busy}
                    onClick={() =>
                      perform(async () => {
                        const r = await rpc(root, "report", {
                          id: selectedRun,
                        });
                        setReport(r.html);
                      })
                    }
                  >
                    完整报告 <ArrowUpRight size={15} />
                  </button>
                </div>
                {result && (
                  <p className="run-caption">
                    当前展示：{selectedRun}
                    <span>修改上方配置不会改变此历史结果</span>
                  </p>
                )}
                <div className="metrics-grid">
                  {[
                    {
                      label: "期末资产",
                      value: money(result?.summary.final_equity),
                      foot: "PORTFOLIO VALUE",
                      cls: "cyan",
                    },
                    {
                      label: "累计收益",
                      value: percent(metrics.total_return),
                      foot: "TOTAL RETURN",
                      cls: "green",
                    },
                    {
                      label: "年化收益",
                      value: percent(metrics.cagr),
                      foot: "ANNUALIZED RETURN",
                      cls: "purple",
                    },
                    {
                      label: "最大回撤",
                      value: percent(metrics.max_drawdown),
                      foot: "MAX DRAWDOWN",
                      cls: "orange",
                    },
                  ].map((m, i) => (
                    <div className={`panel metric ${m.cls}`} key={m.label}>
                      <div>
                        <span>{m.label}</span>
                        <span className="metric-index">0{i + 1}</span>
                      </div>
                      <strong>{m.value}</strong>
                      <small>{m.foot}</small>
                      <span className="metric-decoration" />
                    </div>
                  ))}
                </div>
                <div className="panel chart-panel">
                  <div className="section-header">
                    <div
                      role="tablist"
                      aria-label="结果视图"
                      className="result-tabs"
                    >
                      {(
                        [
                          ["equity", "收益曲线"],
                          ["fills", "成交明细"],
                          ["logs", "运行日志"],
                        ] as const
                      ).map(([key, label]) => (
                        <button
                          role="tab"
                          aria-selected={pane === key}
                          className={pane === key ? "active" : ""}
                          key={key}
                          onClick={() => setPane(key)}
                        >
                          {label}
                          {key === "logs" && running && (
                            <span className="live-dot pulse" />
                          )}
                        </button>
                      ))}
                    </div>
                    <span className="chart-meta">
                      {pane === "equity"
                        ? "累计收益 / %"
                        : pane === "fills"
                          ? `${result?.fills.length || 0} 笔成交`
                          : jobState.toUpperCase()}
                    </span>
                  </div>
                  {pane === "equity" &&
                    (chartData.length ? (
                      <>
                        <div className="chart-legend">
                          <span>
                            <i className="legend-dot" />
                            策略组合
                          </span>
                          {chartData.some((r: any) => r.benchmark) && (
                            <span>
                              <i className="legend-dot benchmark" />
                              基准
                            </span>
                          )}
                          <span className="chart-date">
                            {chartData[0].date} —{" "}
                            {chartData[chartData.length - 1].date}
                          </span>
                        </div>
                        <div
                          className="chart"
                          role="img"
                          aria-label="历史回测累计收益曲线，完整数值可查看报告"
                        >
                          <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart
                              data={chartData}
                              margin={{ top: 8, right: 24, left: 0, bottom: 6 }}
                            >
                              <defs>
                                <linearGradient
                                  id="equityGlow"
                                  x1="0"
                                  y1="0"
                                  x2="0"
                                  y2="1"
                                >
                                  <stop
                                    offset="0%"
                                    stopColor="var(--cyan)"
                                    stopOpacity={0.23}
                                  />
                                  <stop
                                    offset="100%"
                                    stopColor="var(--cyan)"
                                    stopOpacity={0}
                                  />
                                </linearGradient>
                              </defs>
                              <CartesianGrid
                                stroke="var(--grid)"
                                vertical={false}
                                strokeDasharray="3 5"
                              />
                              <XAxis
                                dataKey="date"
                                minTickGap={90}
                                tickFormatter={(s) => s.slice(0, 7)}
                                tick={{ fill: "var(--muted)", fontSize: 11 }}
                                axisLine={false}
                                tickLine={false}
                              />
                              <YAxis
                                tickFormatter={(n) => `${n.toFixed(0)}%`}
                                tick={{ fill: "var(--muted)", fontSize: 11 }}
                                axisLine={false}
                                tickLine={false}
                              />
                              <Tooltip
                                contentStyle={{
                                  background: "var(--surface-solid)",
                                  border: "1px solid var(--border)",
                                  borderRadius: 10,
                                  color: "var(--text)",
                                }}
                                formatter={(v: any, name: any) => [
                                  `${Number(v).toFixed(2)}%`,
                                  name === "equity" ? "策略组合" : "基准",
                                ]}
                              />
                              <Area
                                isAnimationActive={false}
                                type="monotone"
                                dataKey="equity"
                                stroke="var(--cyan)"
                                strokeWidth={2}
                                fill="url(#equityGlow)"
                              />
                              <Line
                                isAnimationActive={false}
                                type="monotone"
                                dataKey="benchmark"
                                stroke="var(--purple)"
                                strokeDasharray="5 4"
                                dot={false}
                                strokeWidth={1.5}
                              />
                            </ComposedChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="chart-bottom">
                          <span>
                            Sharpe <strong>{number(metrics.sharpe)}</strong>
                          </span>
                          <span>
                            平均股票仓位{" "}
                            <strong>
                              {percent(metrics.avg_gross_exposure)}
                            </strong>
                          </span>
                          <span>已计入本次配置的手续费与滑点</span>
                        </div>
                      </>
                    ) : (
                      <div className="empty">
                        <Activity size={30} />
                        <p>运行一次回测，查看真实收益曲线。</p>
                      </div>
                    ))}
                  {pane === "fills" && (
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            {[
                              "成交日期",
                              "股票",
                              "方向",
                              "数量",
                              "成交价",
                              "手续费",
                            ].map((h) => (
                              <th key={h}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {result?.fills.map((r: any, i: number) => (
                            <tr key={i}>
                              <td>{r.date || r.timestamp}</td>
                              <td>{r.symbol}</td>
                              <td>
                                <span
                                  className={
                                    r.side === "buy" ? "buy-tag" : "sell-tag"
                                  }
                                >
                                  {r.side}
                                </span>
                              </td>
                              <td>{r.quantity || r.qty}</td>
                              <td>{number(r.price || r.fill_price)}</td>
                              <td>{number(r.commission)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {!result?.fills.length && (
                        <div className="empty">暂无成交记录</div>
                      )}
                    </div>
                  )}
                  {pane === "logs" && (
                    <pre className="logs" aria-live="polite">
                      {log ||
                        "尚未从此窗口启动回测。历史实验日志可在对应 runs 目录查看。"}
                    </pre>
                  )}
                </div>
                {result?.warnings?.length > 0 && (
                  <details className="result-warnings">
                    <summary>
                      本次回测假设与提示（{result.warnings.length}）
                    </summary>
                    <ul>
                      {result.warnings.map((w: any, i: number) => (
                        <li key={i}>
                          {typeof w === "string" ? w : JSON.stringify(w)}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </section>
            </>
          )}
          {page === "history" && (
            <div className="panel history-panel">
              <div className="section-header">
                <div>
                  <History size={18} />
                  <h2>实验档案</h2>
                </div>
                <span className="micro-badge">最近 {history.length} 次</span>
              </div>
              {history.length ? (
                history.map((h) => (
                  <button
                    className="history-row"
                    key={h.id}
                    disabled={busy || h.status !== "complete"}
                    onClick={() => perform(() => chooseRun(h.id))}
                  >
                    <div className="history-icon">
                      <FlaskConical size={20} />
                    </div>
                    <div>
                      <strong>{h.id}</strong>
                      <small>
                        {h.status === "complete"
                          ? "已完成 · 输入快照已冻结"
                          : `失败 · ${h.error || ""}`}
                      </small>
                    </div>
                    <div className="history-value">
                      {money(h.final_equity)}
                      <small>{percent(h.metrics?.total_return)}</small>
                    </div>
                    <ArrowUpRight size={18} />
                  </button>
                ))
              ) : (
                <div className="empty">暂无回测记录</div>
              )}
            </div>
          )}
          {page === "data" && (
            <div className="panel">
              <div className="section-header">
                <div>
                  <Database size={18} />
                  <h2>本地行情文件</h2>
                </div>
                <span className="micro-badge">CSV / PARQUET</span>
              </div>
              <p className="info-text">
                读取工作区 data
                目录。把行情文件放入此目录后刷新，即可在回测配置中选择。数据完整性由引擎在回测时校验。
              </p>
              {catalog?.data.map((d) => (
                <div className="data-row" key={d.path}>
                  <Database size={20} />
                  <div>
                    <strong>{short(d.path)}</strong>
                    <small>{d.path}</small>
                  </div>
                  <span>{(d.bytes / 1024).toFixed(1)} KB</span>
                </div>
              ))}
              {!catalog?.data.length && (
                <div className="empty">data 目录暂无行情文件</div>
              )}
            </div>
          )}
          {page === "settings" && (
            <div className="panel settings-panel">
              <div className="section-header">
                <div>
                  <FolderOpen size={18} />
                  <h2>连接本地工作区</h2>
                </div>
              </div>
              <div className="settings-body">
                <p>
                  选择现有 QuantLab 项目根目录。App 使用该目录的 Python
                  环境、策略、因子、行情和回测档案。
                </p>
                <label>
                  工作区绝对路径
                  <input
                    aria-label="工作区绝对路径"
                    value={rootInput}
                    onChange={(e) => setRootInput(e.target.value)}
                    placeholder="/Users/you/QuantLab"
                  />
                </label>
                <button
                  className="primary"
                  disabled={busy || running || dirty}
                  onClick={() =>
                    perform(async () => {
                      setDocs({});
                      docRef.current = {};
                      setResult(null);
                      setSelectedRun("");
                      await connect(rootInput);
                      notify("工作区已连接");
                      setPage("studio");
                    })
                  }
                >
                  <FolderOpen size={16} /> 连接工作区
                </button>
                {dirty && <p>请先保存编辑中的文件，再切换工作区。</p>}
                <div className="settings-detail">
                  <Cpu size={20} />
                  <div>
                    <strong>本地 Python 引擎</strong>
                    <p>
                      需要工作区已有 .venv/bin/python。本版 App 不内置
                      Python，运行你自己信任的策略代码；独立进程不等于安全沙箱。
                    </p>
                  </div>
                </div>
                <div className="settings-detail">
                  <ShieldCheck size={20} />
                  <div>
                    <strong>本地研究数据</strong>
                    <p>
                      界面不会自动同步到
                      GitHub。策略、因子与回测结果保留在本机。
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
          <footer className="app-footer">
            <span>
              <Activity size={12} /> QUANTLAB / RESEARCH FIRST
            </span>
            <span>本地计算 · 可复现回测 · 无实盘交易</span>
          </footer>
        </div>
      </main>
      {report && (
        <div className="modal-backdrop">
          <section
            role="dialog"
            aria-modal="true"
            aria-label="完整回测报告"
            className="report-modal"
          >
            <div className="section-header">
              <div>
                <BookOpen size={18} />
                <h2>完整回测报告</h2>
              </div>
              <button
                className="icon-button"
                autoFocus
                aria-label="关闭报告"
                onClick={() => setReport(null)}
              >
                <X size={20} />
              </button>
            </div>
            <iframe sandbox="" title="完整回测报告" srcDoc={report} />
          </section>
        </div>
      )}
      {reloadPath && (
        <div className="modal-backdrop">
          <section
            role="dialog"
            aria-modal="true"
            aria-label="重新读取文件"
            className="panel new-file-modal"
          >
            <div className="section-header">
              <h2>重新读取磁盘文件</h2>
            </div>
            <div className="settings-body">
              <p>
                重新加载 {short(reloadPath)}
                ，将放弃此文件在编辑区尚未保存的修改。磁盘上的文件保持不变。
              </p>
              <div className="heading-actions">
                <button
                  autoFocus
                  className="secondary"
                  onClick={() => setReloadPath(null)}
                >
                  保留编辑
                </button>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    perform(async () => {
                      const d = await rpc(root, "read", { path: reloadPath });
                      setDocs((prev) => ({
                        ...prev,
                        [reloadPath]: { ...d, saved: d.text },
                      }));
                      setReloadPath(null);
                      notify("已重新读取磁盘文件");
                    })
                  }
                >
                  放弃编辑并重新读取
                </button>
              </div>
            </div>
          </section>
        </div>
      )}
      {newFile && (
        <div className="modal-backdrop">
          <form
            role="dialog"
            aria-modal="true"
            aria-label="新建代码文件"
            className="panel new-file-modal"
            onSubmit={(e) => {
              e.preventDefault();
              perform(createFile);
            }}
          >
            <div className="section-header">
              <h2>新建{newFile === "strategies" ? "策略" : "因子"}文件</h2>
              <button
                type="button"
                className="icon-button"
                aria-label="关闭新建文件"
                onClick={() => setNewFile(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="settings-body">
              <label>
                Python 文件名
                <input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="my_strategy.py"
                />
              </label>
              <p>保存至 {newFile}/，不会覆盖已有文件。</p>
              <button className="primary" disabled={busy} type="submit">
                <Plus size={16} /> 创建文件
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
