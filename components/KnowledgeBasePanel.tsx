"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { KnowledgeEntry, KnowledgeEntryInput } from "@/types/knowledge";

const emptyInput: KnowledgeEntryInput = {
  title: "",
  content: "",
  sourceFileName: "",
  sourceType: "",
  tags: []
};

type KnowledgeFilters = {
  search: string;
  sourceType: string;
  tag: string;
};

const emptyFilters: KnowledgeFilters = {
  search: "",
  sourceType: "",
  tag: ""
};

async function readJsonResponse<T>(response: Response, fallbackMessage: string) {
  const text = await response.text();
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(response.ok ? fallbackMessage : `${fallbackMessage}：服务返回了非 JSON 错误页`);
  }
}

type PreviewChunk = KnowledgeEntryInput & {
  previewId: string;
  selected: boolean;
  tagsText: string;
};

type ImportPreview = {
  sourceFileName: string;
  sourceType: string;
  chunks: PreviewChunk[];
};

export default function KnowledgeBasePanel() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [selected, setSelected] = useState<KnowledgeEntry | null>(null);
  const [editing, setEditing] = useState<KnowledgeEntry | null>(null);
  const [form, setForm] = useState<KnowledgeEntryInput>(emptyInput);
  const [tagsText, setTagsText] = useState("");
  const [filters, setFilters] = useState<KnowledgeFilters>(emptyFilters);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");
  const [transferStatus, setTransferStatus] = useState("");
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const sourceTypes = useMemo(
    () => Array.from(new Set(entries.map((entry) => entry.sourceType).filter(Boolean))).sort(),
    [entries]
  );

  const allTags = useMemo(
    () => Array.from(new Set(entries.flatMap((entry) => entry.tags))).sort(),
    [entries]
  );

  async function loadEntries(nextFilters = filters) {
    setLoading(true);
    setError("");
    setTransferStatus("");
    const params = new URLSearchParams();
    Object.entries(nextFilters).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      }
    });

    try {
      const response = await fetch(`/api/knowledge?${params.toString()}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("知识条目加载失败");
      }

      const data = (await response.json()) as KnowledgeEntry[];
      setEntries(data);
      setSelected((current) => {
        if (!current) {
          return data[0] ?? null;
        }
        return data.find((entry) => entry.id === current.id) ?? data[0] ?? null;
      });
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "知识条目加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadEntries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function beginCreate() {
    setEditing(null);
    setForm(emptyInput);
    setTagsText("");
    setError("");
  }

  function beginEdit(entry: KnowledgeEntry) {
    setEditing(entry);
    setForm({
      title: entry.title,
      content: entry.content,
      sourceFileName: entry.sourceFileName,
      sourceType: entry.sourceType,
      tags: [...entry.tags]
    });
    setTagsText(entry.tags.join(", "));
    setError("");
  }

  function updateField<K extends keyof KnowledgeEntryInput>(field: K, value: KnowledgeEntryInput[K]) {
    setForm((current) => ({
      ...current,
      [field]: value
    }));
  }

  function validateForm() {
    const errors: string[] = [];
    const requiredFields: Array<[keyof KnowledgeEntryInput, string]> = [
      ["title", "标题"],
      ["content", "内容"],
      ["sourceFileName", "来源文件名"],
      ["sourceType", "来源类型"]
    ];

    requiredFields.forEach(([field, label]) => {
      if (typeof form[field] !== "string" || !String(form[field]).trim()) {
        errors.push(`${label}不能为空`);
      }
    });

    return errors;
  }

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors = validateForm();
    if (errors.length > 0) {
      setError(errors.join("；"));
      return;
    }

    setSaving(true);
    setError("");

    const payload: KnowledgeEntryInput = {
      ...form,
      title: form.title.trim(),
      content: form.content.trim(),
      sourceFileName: form.sourceFileName.trim(),
      sourceType: form.sourceType.trim(),
      tags: tagsText
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean)
    };

    try {
      const response = await fetch(editing ? `/api/knowledge/${editing.id}` : "/api/knowledge", {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const result = (await response.json()) as KnowledgeEntry | { error?: string };
      if (!response.ok) {
        throw new Error("error" in result ? result.error : "保存失败");
      }

      setEditing(null);
      setForm(emptyInput);
      setTagsText("");
      await loadEntries();
      setSelected(result as KnowledgeEntry);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function removeEntry(entry: KnowledgeEntry) {
    const confirmed = window.confirm(`确定删除知识条目「${entry.title}」吗？`);
    if (!confirmed) {
      return;
    }

    setError("");
    const response = await fetch(`/api/knowledge/${entry.id}`, { method: "DELETE" });
    if (!response.ok) {
      setError("删除失败");
      return;
    }

    await loadEntries();
    beginCreate();
  }

  function updateFilter(field: keyof KnowledgeFilters, value: string) {
    const nextFilters = { ...filters, [field]: value };
    setFilters(nextFilters);
    void loadEntries(nextFilters);
  }

  async function exportJson() {
    setError("");
    setTransferStatus("");

    try {
      const response = await fetch("/api/knowledge/export");
      if (!response.ok) {
        throw new Error("导出失败");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "ai-literacy-knowledge-base.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setTransferStatus("导出完成：已下载 ai-literacy-knowledge-base.json");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "导出失败");
    }
  }

  async function parseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setParsing(true);
    setError("");
    setTransferStatus("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch("/api/knowledge/parse", {
        method: "POST",
        body: formData
      });
      const result = await readJsonResponse<{
        sourceFileName?: string;
        sourceType?: string;
        chunks?: KnowledgeEntryInput[];
        error?: string;
      }>(response, "文件解析失败");

      if (!response.ok) {
        throw new Error(result.error || "文件解析失败");
      }

      const chunks = (result.chunks ?? []).map((chunk, index) => ({
        ...chunk,
        previewId: `${Date.now()}-${index}`,
        selected: true,
        tagsText: chunk.tags.join(", ")
      }));

      if (chunks.length === 0) {
        throw new Error("未提取到可导入的文本内容");
      }

      setImportPreview({
        sourceFileName: result.sourceFileName || file.name,
        sourceType: result.sourceType || "",
        chunks
      });
      setTransferStatus(`解析完成：已切分为 ${chunks.length} 个知识片段，请预览后确认导入`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "文件解析失败");
    } finally {
      setParsing(false);
      event.target.value = "";
    }
  }

  function updatePreviewChunk<K extends keyof PreviewChunk>(previewId: string, field: K, value: PreviewChunk[K]) {
    setImportPreview((current) => {
      if (!current) {
        return current;
      }

      return {
        ...current,
        chunks: current.chunks.map((chunk) =>
          chunk.previewId === previewId ? { ...chunk, [field]: value } : chunk
        )
      };
    });
  }

  function removePreviewChunk(previewId: string) {
    setImportPreview((current) => {
      if (!current) {
        return current;
      }

      const chunks = current.chunks.filter((chunk) => chunk.previewId !== previewId);
      return chunks.length > 0 ? { ...current, chunks } : null;
    });
  }

  async function confirmImport() {
    if (!importPreview) {
      return;
    }

    const selectedChunks = importPreview.chunks.filter((chunk) => chunk.selected);
    if (selectedChunks.length === 0) {
      setError("请至少选择一个知识片段");
      return;
    }

    const invalid = selectedChunks.find((chunk) => !chunk.title.trim() || !chunk.content.trim());
    if (invalid) {
      setError("选中的知识片段需要保留标题和内容");
      return;
    }

    setImporting(true);
    setError("");

    const payload: KnowledgeEntryInput[] = selectedChunks.map((chunk) => ({
      title: chunk.title.trim(),
      content: chunk.content.trim(),
      sourceFileName: chunk.sourceFileName.trim(),
      sourceType: chunk.sourceType.trim(),
      tags: chunk.tagsText
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean)
    }));

    try {
      const response = await fetch("/api/knowledge/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await readJsonResponse<{ imported?: number; total?: number; error?: string }>(
        response,
        "导入失败"
      );
      if (!response.ok) {
        throw new Error(result.error || "导入失败");
      }

      setImportPreview(null);
      await loadEntries();
      setTransferStatus(`导入完成：本次 ${result.imported} 条，知识库共 ${result.total} 条`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "导入失败");
    } finally {
      setImporting(false);
    }
  }

  return (
    <>
      <section className="section-heading">
        <div>
          <h2>知识库</h2>
          <p>本地 SQLite 管理知识条目，支持文件解析、切分、预览后导入。</p>
        </div>
        <div className="toolbar">
          <button className="primary" type="button" onClick={beginCreate}>
            新增知识
          </button>
          <button type="button" onClick={() => fileInputRef.current?.click()} disabled={parsing}>
            {parsing ? "解析中..." : "导入文件"}
          </button>
          <button type="button" onClick={() => void exportJson()}>
            导出 JSON
          </button>
          <input
            ref={fileInputRef}
            className="file-input"
            type="file"
            accept=".pdf,.docx,.txt,.md,.json,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,application/json"
            onChange={parseFile}
          />
        </div>
      </section>

      <section className="filters" aria-label="知识库筛选">
        <input
          className="search"
          placeholder="搜索标题、内容或来源文件名"
          value={filters.search}
          onChange={(event) => updateFilter("search", event.target.value)}
        />
        <select value={filters.sourceType} onChange={(event) => updateFilter("sourceType", event.target.value)}>
          <option value="">全部来源类型</option>
          {sourceTypes.map((sourceType) => (
            <option key={sourceType} value={sourceType}>
              {sourceType}
            </option>
          ))}
        </select>
        <input
          list="knowledge-tag-options"
          placeholder="按标签筛选"
          value={filters.tag}
          onChange={(event) => updateFilter("tag", event.target.value)}
        />
        <datalist id="knowledge-tag-options">
          {allTags.map((tag) => (
            <option key={tag} value={tag} />
          ))}
        </datalist>
      </section>

      {error ? <div className="error-box">{error}</div> : null}
      {transferStatus ? <div className="status-box">{transferStatus}</div> : null}
      {importPreview ? (
        <ImportPreviewPanel
          preview={importPreview}
          importing={importing}
          onCancel={() => setImportPreview(null)}
          onConfirm={() => void confirmImport()}
          onChunkChange={updatePreviewChunk}
          onChunkRemove={removePreviewChunk}
        />
      ) : null}

      <section className="layout-grid">
        <div>
          <section className="panel">
            <div className="panel-header">
              <h2>知识列表</h2>
              <span className="muted">{loading ? "加载中..." : `${entries.length} 条`}</span>
            </div>
            <div className="table-scroll">
              <table className="question-table">
                <thead>
                  <tr>
                    <th style={{ width: "34%" }}>标题</th>
                    <th>来源类型</th>
                    <th>来源文件</th>
                    <th>标签</th>
                    <th style={{ width: 150 }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => (
                    <tr
                      key={entry.id}
                      className={selected?.id === entry.id ? "selected" : ""}
                      onClick={() => setSelected(entry)}
                    >
                      <td className="title-cell">
                        <strong>{entry.title}</strong>
                        <span>{entry.content}</span>
                      </td>
                      <td>{entry.sourceType}</td>
                      <td>{entry.sourceFileName}</td>
                      <td>
                        <div className="badge-row">
                          {entry.tags.slice(0, 3).map((tag) => (
                            <span className="badge" key={tag}>
                              {tag}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <div className="actions">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              beginEdit(entry);
                            }}
                          >
                            编辑
                          </button>
                          <button
                            className="danger"
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              void removeEntry(entry);
                            }}
                          >
                            删除
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!loading && entries.length === 0 ? <div className="empty-state">暂无知识条目，可新增一条。</div> : null}
          </section>

          <KnowledgeForm
            editing={editing}
            form={form}
            tagsText={tagsText}
            saving={saving}
            onSubmit={submitForm}
            onCancel={beginCreate}
            onFieldChange={updateField}
            onTagsTextChange={setTagsText}
          />
        </div>

        <KnowledgeDetail
          entry={selected}
          onEdit={beginEdit}
          onDelete={(entry) => {
            void removeEntry(entry);
          }}
        />
      </section>
    </>
  );
}

type ImportPreviewPanelProps = {
  preview: ImportPreview;
  importing: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  onChunkChange: <K extends keyof PreviewChunk>(previewId: string, field: K, value: PreviewChunk[K]) => void;
  onChunkRemove: (previewId: string) => void;
};

function ImportPreviewPanel({
  preview,
  importing,
  onCancel,
  onConfirm,
  onChunkChange,
  onChunkRemove
}: ImportPreviewPanelProps) {
  const selectedCount = preview.chunks.filter((chunk) => chunk.selected).length;

  return (
    <section className="panel import-preview">
      <div className="panel-header">
        <div>
          <h2>导入预览</h2>
          <span className="muted">
            {preview.sourceFileName} · {preview.sourceType} · 已选 {selectedCount}/{preview.chunks.length}
          </span>
        </div>
        <div className="actions">
          <button type="button" onClick={onCancel}>
            取消
          </button>
          <button className="primary" type="button" onClick={onConfirm} disabled={importing || selectedCount === 0}>
            {importing ? "导入中..." : "确认导入"}
          </button>
        </div>
      </div>
      <div className="import-preview-list">
        {preview.chunks.map((chunk, index) => (
          <section className="chunk-editor" key={chunk.previewId}>
            <div className="chunk-editor-header">
              <label className="chunk-check">
                <input
                  type="checkbox"
                  checked={chunk.selected}
                  onChange={(event) => onChunkChange(chunk.previewId, "selected", event.target.checked)}
                />
                <span>片段 {index + 1}</span>
              </label>
              <button className="danger" type="button" onClick={() => onChunkRemove(chunk.previewId)}>
                删除片段
              </button>
            </div>
            <div className="form-grid">
              <label className="form-row">
                <span>标题</span>
                <input
                  value={chunk.title}
                  onChange={(event) => onChunkChange(chunk.previewId, "title", event.target.value)}
                />
              </label>
              <label className="form-row">
                <span>标签，用英文逗号分隔</span>
                <input
                  value={chunk.tagsText}
                  onChange={(event) => onChunkChange(chunk.previewId, "tagsText", event.target.value)}
                />
              </label>
              <label className="form-row full">
                <span>内容（{chunk.content.length} 字）</span>
                <textarea
                  value={chunk.content}
                  onChange={(event) => onChunkChange(chunk.previewId, "content", event.target.value)}
                />
              </label>
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}

type KnowledgeFormProps = {
  editing: KnowledgeEntry | null;
  form: KnowledgeEntryInput;
  tagsText: string;
  saving: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onFieldChange: <K extends keyof KnowledgeEntryInput>(field: K, value: KnowledgeEntryInput[K]) => void;
  onTagsTextChange: (value: string) => void;
};

function KnowledgeForm({
  editing,
  form,
  tagsText,
  saving,
  onSubmit,
  onCancel,
  onFieldChange,
  onTagsTextChange
}: KnowledgeFormProps) {
  return (
    <section className="form-panel">
      <div className="form-header">
        <h2>{editing ? "编辑知识" : "新增知识"}</h2>
        {editing ? (
          <button type="button" onClick={onCancel}>
            取消编辑
          </button>
        ) : null}
      </div>
      <form className="form-body" onSubmit={onSubmit}>
        <div className="form-grid">
          <label className="form-row full">
            <span>标题</span>
            <input value={form.title} onChange={(event) => onFieldChange("title", event.target.value)} required />
          </label>
          <label className="form-row full">
            <span>内容</span>
            <textarea value={form.content} onChange={(event) => onFieldChange("content", event.target.value)} required />
          </label>
          <label className="form-row">
            <span>来源文件名</span>
            <input
              value={form.sourceFileName}
              onChange={(event) => onFieldChange("sourceFileName", event.target.value)}
              required
            />
          </label>
          <label className="form-row">
            <span>来源类型</span>
            <input value={form.sourceType} onChange={(event) => onFieldChange("sourceType", event.target.value)} required />
          </label>
          <label className="form-row full">
            <span>标签，用英文逗号分隔</span>
            <input value={tagsText} onChange={(event) => onTagsTextChange(event.target.value)} />
          </label>
        </div>
        <div className="toolbar" style={{ marginTop: 14 }}>
          <button className="primary" type="submit" disabled={saving}>
            {saving ? "保存中..." : editing ? "保存修改" : "创建知识"}
          </button>
          <button type="button" onClick={onCancel}>
            重置表单
          </button>
        </div>
      </form>
    </section>
  );
}

type KnowledgeDetailProps = {
  entry: KnowledgeEntry | null;
  onEdit: (entry: KnowledgeEntry) => void;
  onDelete: (entry: KnowledgeEntry) => void;
};

function KnowledgeDetail({ entry, onEdit, onDelete }: KnowledgeDetailProps) {
  if (!entry) {
    return (
      <aside className="detail-panel">
        <div className="detail-header">
          <h2>知识详情</h2>
        </div>
        <div className="empty-state">选择一条知识查看详情。</div>
      </aside>
    );
  }

  return (
    <aside className="detail-panel">
      <div className="detail-header">
        <h2>知识详情</h2>
        <div className="actions">
          <button type="button" onClick={() => onEdit(entry)}>
            编辑
          </button>
          <button className="danger" type="button" onClick={() => onDelete(entry)}>
            删除
          </button>
        </div>
      </div>
      <div className="detail-body">
        <h3>{entry.title}</h3>
        <p>{entry.content}</p>

        <h3>来源</h3>
        <p>{entry.sourceFileName}</p>
        <span className="badge">{entry.sourceType}</span>

        <h3>标签</h3>
        <div className="badge-row">
          {entry.tags.length > 0 ? entry.tags.map((tag) => <span className="badge" key={tag}>{tag}</span>) : "无"}
        </div>

        <p className="muted">创建：{new Date(entry.createdAt).toLocaleString()}</p>
        <p className="muted">更新：{new Date(entry.updatedAt).toLocaleString()}</p>
      </div>
    </aside>
  );
}
