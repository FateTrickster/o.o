"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { aiLiteracyDimensions, getSecondaryDimensions } from "@/lib/aiLiteracyFramework";
import DraftGeneratorPanel from "@/components/DraftGeneratorPanel";
import KnowledgeBasePanel from "@/components/KnowledgeBasePanel";
import {
  CognitiveLevel,
  DifficultyEstimate,
  Question,
  QuestionInput,
  QuestionOption,
  QuestionStatus,
  QuestionType
} from "@/types/question";

type ActiveModule = "questions" | "knowledge" | "drafts";

const statusOptions: QuestionStatus[] = ["draft", "reviewed", "tested", "retired"];
const difficultyOptions: DifficultyEstimate[] = ["easy", "medium", "hard"];
const questionTypeOptions: QuestionType[] = [
  "单选",
  "多选",
  "判断",
  "填空",
  "案例分析",
  "情景任务",
  "挑战任务",
  "技术主观题",
  "情境决策题",
  "短答建构题",
  "案例分析题",
  "解释理由题",
  "过程说明题",
  "方案设计题",
  "项目任务题"
];
const cognitiveOptions: CognitiveLevel[] = [
  "remember",
  "understand",
  "apply",
  "analyze",
  "evaluate",
  "create"
];

const emptyInput: QuestionInput = {
  questionType: "单选",
  title: "",
  question: "",
  scenario: "",
  options: [
    { id: "A", text: "" },
    { id: "B", text: "" },
    { id: "C", text: "" },
    { id: "D", text: "" }
  ],
  correctAnswer: "A",
  explanation: "",
  dimension: "",
  secondaryDimension: "",
  tertiaryDimension: "",
  quaternaryDimension: "",
  subSkill: "",
  cognitiveLevel: "understand",
  difficultyEstimate: "medium",
  tags: [],
  knowledgePoints: [],
  sourceReference: "",
  status: "draft"
};

type Filters = {
  dimension: string;
  secondaryDimension: string;
  status: string;
  difficulty: string;
  tag: string;
  search: string;
};

const emptyFilters: Filters = {
  dimension: "",
  secondaryDimension: "",
  status: "",
  difficulty: "",
  tag: "",
  search: ""
};

function statusText(status: QuestionStatus) {
  const map: Record<QuestionStatus, string> = {
    draft: "草稿",
    reviewed: "已审",
    tested: "已测",
    retired: "停用"
  };
  return map[status];
}

function difficultyText(difficulty: DifficultyEstimate) {
  const map: Record<DifficultyEstimate, string> = {
    easy: "简单",
    medium: "中等",
    hard: "困难"
  };
  return map[difficulty];
}

function cognitiveText(level: CognitiveLevel) {
  const map: Record<CognitiveLevel, string> = {
    remember: "记忆",
    understand: "理解",
    apply: "应用",
    analyze: "分析",
    evaluate: "评价",
    create: "创造"
  };
  return map[level];
}

export default function QuestionBankApp() {
  const [activeModule, setActiveModule] = useState<ActiveModule>("questions");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [selected, setSelected] = useState<Question | null>(null);
  const [editing, setEditing] = useState<Question | null>(null);
  const [form, setForm] = useState<QuestionInput>(emptyInput);
  const [tagsText, setTagsText] = useState("");
  const [knowledgePointsText, setKnowledgePointsText] = useState("");
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [transferStatus, setTransferStatus] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const dimensions = aiLiteracyDimensions;

  const secondaryDimensions = useMemo(
    () => (filters.dimension ? getSecondaryDimensions(filters.dimension) : []),
    [filters.dimension]
  );

  const formSecondaryDimensions = useMemo(
    () => (form.dimension ? getSecondaryDimensions(form.dimension) : []),
    [form.dimension]
  );

  const allTags = useMemo(
    () => Array.from(new Set(questions.flatMap((item) => item.tags))).sort(),
    [questions]
  );

  async function loadQuestions(nextFilters = filters) {
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
      const response = await fetch(`/api/questions?${params.toString()}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("题目加载失败");
      }

      const data = (await response.json()) as Question[];
      setQuestions(data);
      setSelected((current) => {
        if (!current) {
          return data[0] ?? null;
        }
        return data.find((item) => item.id === current.id) ?? data[0] ?? null;
      });
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "题目加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadQuestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function beginCreate() {
    setEditing(null);
    setForm({ ...emptyInput, options: emptyInput.options.map((option) => ({ ...option })) });
    setTagsText("");
    setKnowledgePointsText("");
    setError("");
  }

  function beginEdit(question: Question) {
    setEditing(question);
    setForm({
      questionType: question.questionType || "单选",
      title: question.title,
      question: question.question,
      scenario: question.scenario,
      options: question.options.map((option) => ({ ...option })),
      correctAnswer: question.correctAnswer,
      explanation: question.explanation,
      dimension: question.dimension,
      secondaryDimension: question.secondaryDimension,
      tertiaryDimension: question.tertiaryDimension || "",
      quaternaryDimension: question.quaternaryDimension || "",
      subSkill: question.subSkill,
      cognitiveLevel: question.cognitiveLevel,
      difficultyEstimate: question.difficultyEstimate,
      tags: [...question.tags],
      knowledgePoints: [...(question.knowledgePoints || [])],
      sourceReference: question.sourceReference,
      status: question.status
    });
    setTagsText(question.tags.join(", "));
    setKnowledgePointsText((question.knowledgePoints || []).join(", "));
    setError("");
  }

  function updateField<K extends keyof QuestionInput>(field: K, value: QuestionInput[K]) {
    setForm((current) => ({
      ...current,
      [field]: value,
      ...(field === "dimension"
        ? { secondaryDimension: "", tertiaryDimension: "", quaternaryDimension: "", knowledgePoints: [] }
        : {}),
      ...(field === "secondaryDimension" ? { tertiaryDimension: "", quaternaryDimension: "", knowledgePoints: [] } : {}),
      ...(field === "tertiaryDimension" ? { quaternaryDimension: "", knowledgePoints: [] } : {})
    }));
    if (field === "dimension" || field === "secondaryDimension" || field === "tertiaryDimension") {
      setKnowledgePointsText("");
    }
  }

  function updateOption(index: number, field: keyof QuestionOption, value: string) {
    setForm((current) => ({
      ...current,
      options: current.options.map((option, optionIndex) =>
        optionIndex === index ? { ...option, [field]: value } : option
      )
    }));
  }

  function addOption() {
    const nextId = String.fromCharCode(65 + form.options.length);
    setForm((current) => ({
      ...current,
      options: [...current.options, { id: nextId, text: "" }]
    }));
  }

  function removeOption(index: number) {
    setForm((current) => {
      const options = current.options.filter((_, optionIndex) => optionIndex !== index);
      const correctAnswer = options.some((option) => option.id === current.correctAnswer)
        ? current.correctAnswer
        : options[0]?.id ?? "";

      return {
        ...current,
        options,
        correctAnswer
      };
    });
  }

  function validateForm() {
    const errors: string[] = [];
    const requiredFields: Array<[keyof QuestionInput, string]> = [
      ["title", "标题"],
      ["question", "题干"],
      ["scenario", "场景"],
      ["explanation", "解析"],
      ["dimension", "一级维度"],
      ["secondaryDimension", "二级维度"],
      ["subSkill", "二级能力"],
      ["sourceReference", "来源"]
    ];

    requiredFields.forEach(([field, label]) => {
      if (typeof form[field] !== "string" || !String(form[field]).trim()) {
        errors.push(`${label}不能为空`);
      }
    });

    const validOptions = form.options.filter((option) => option.id.trim() && option.text.trim());
    if (validOptions.length < 2) {
      errors.push("至少需要 2 个完整选项");
    }

    if (!validOptions.some((option) => option.id === form.correctAnswer)) {
      errors.push("正确答案必须匹配一个选项编号");
    }

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

    const payload: QuestionInput = {
      ...form,
      options: form.options
        .map((option) => ({ id: option.id.trim(), text: option.text.trim() }))
        .filter((option) => option.id && option.text),
      tags: tagsText
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
      knowledgePoints: knowledgePointsText
        .split(",")
        .map((point) => point.trim())
        .filter(Boolean)
    };

    try {
      const response = await fetch(editing ? `/api/questions/${editing.id}` : "/api/questions", {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const result = (await response.json()) as Question | { error?: string };
      if (!response.ok) {
        throw new Error("error" in result ? result.error : "保存失败");
      }

      setEditing(null);
      setForm({ ...emptyInput, options: emptyInput.options.map((option) => ({ ...option })) });
      setTagsText("");
      setKnowledgePointsText("");
      await loadQuestions();
      setSelected(result as Question);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function removeQuestion(question: Question) {
    const confirmed = window.confirm(`确定删除题目「${question.title}」吗？`);
    if (!confirmed) {
      return;
    }

    setError("");
    const response = await fetch(`/api/questions/${question.id}`, { method: "DELETE" });
    if (!response.ok) {
      setError("删除失败");
      return;
    }

    await loadQuestions();
    beginCreate();
  }

  function updateFilter(field: keyof Filters, value: string) {
    const nextFilters =
      field === "dimension"
        ? { ...filters, dimension: value, secondaryDimension: "" }
        : { ...filters, [field]: value };
    setFilters(nextFilters);
    void loadQuestions(nextFilters);
  }

  async function importJson(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setError("");
    try {
      const text = await file.text();
      const payload = JSON.parse(text) as Question[];
      const response = await fetch("/api/questions/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = (await response.json()) as { imported?: number; total?: number; error?: string };
      if (!response.ok) {
        throw new Error(result.error || "导入失败");
      }

      await loadQuestions();
      setTransferStatus(`导入完成：本次 ${result.imported} 道，题库共 ${result.total} 道`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "导入失败，请检查 JSON 格式");
    } finally {
      event.target.value = "";
    }
  }

  async function exportJson() {
    setError("");
    setTransferStatus("");

    try {
      const response = await fetch("/api/questions/export");
      if (!response.ok) {
        throw new Error("导出失败");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "ai-literacy-question-bank.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setTransferStatus("导出完成：已下载 ai-literacy-question-bank.json");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "导出失败");
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>AI素养测评题库系统</h1>
          <p>本地 FastAPI + SQLite 的题库管理 MVP，当前聚焦题目维护和数据进出。</p>
        </div>
        {activeModule === "questions" ? (
          <div className="toolbar">
            <button className="primary" type="button" onClick={beginCreate}>
              新增题目
            </button>
            <button type="button" onClick={() => fileInputRef.current?.click()}>
              导入 JSON
            </button>
            <button type="button" onClick={() => void exportJson()}>
              导出 JSON
            </button>
            <input
              ref={fileInputRef}
              className="file-input"
              type="file"
              accept="application/json,.json"
              onChange={importJson}
            />
          </div>
        ) : null}
      </header>

      <nav className="module-nav" aria-label="模块导航">
        <button
          className={activeModule === "questions" ? "active" : ""}
          type="button"
          onClick={() => setActiveModule("questions")}
        >
          题库管理
        </button>
        <button
          className={activeModule === "knowledge" ? "active" : ""}
          type="button"
          onClick={() => setActiveModule("knowledge")}
        >
          知识库
        </button>
        <button
          className={activeModule === "drafts" ? "active" : ""}
          type="button"
          onClick={() => setActiveModule("drafts")}
        >
          出题草稿
        </button>
      </nav>

      {activeModule === "knowledge" ? <KnowledgeBasePanel /> : null}
      {activeModule === "drafts" ? <DraftGeneratorPanel /> : null}

      {activeModule === "questions" ? (
        <>
      <section className="filters" aria-label="题目筛选">
        <input
          className="search"
          placeholder="搜索编号、题干、标题或场景"
          value={filters.search}
          onChange={(event) => updateFilter("search", event.target.value)}
        />
        <select value={filters.dimension} onChange={(event) => updateFilter("dimension", event.target.value)}>
          <option value="">全部一级维度</option>
          {dimensions.map((dimension) => (
            <option key={dimension} value={dimension}>
              {dimension}
            </option>
          ))}
        </select>
        <select
          value={filters.secondaryDimension}
          onChange={(event) => updateFilter("secondaryDimension", event.target.value)}
          disabled={!filters.dimension}
        >
          <option value="">{filters.dimension ? "全部二级维度" : "先选一级维度"}</option>
          {secondaryDimensions.map((dimension) => (
            <option key={dimension} value={dimension}>
              {dimension}
            </option>
          ))}
        </select>
        <select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}>
          <option value="">全部状态</option>
          {statusOptions.map((status) => (
            <option key={status} value={status}>
              {statusText(status)}
            </option>
          ))}
        </select>
        <select value={filters.difficulty} onChange={(event) => updateFilter("difficulty", event.target.value)}>
          <option value="">全部难度</option>
          {difficultyOptions.map((difficulty) => (
            <option key={difficulty} value={difficulty}>
              {difficultyText(difficulty)}
            </option>
          ))}
        </select>
        <input
          list="tag-options"
          placeholder="按标签筛选"
          value={filters.tag}
          onChange={(event) => updateFilter("tag", event.target.value)}
        />
        <datalist id="tag-options">
          {allTags.map((tag) => (
            <option key={tag} value={tag} />
          ))}
        </datalist>
      </section>

      {error ? <div className="error-box">{error}</div> : null}
      {transferStatus ? <div className="status-box">{transferStatus}</div> : null}

      <section className="layout-grid">
        <div>
          <section className="panel">
            <div className="panel-header">
              <h2>题目列表</h2>
              <span className="muted">{loading ? "加载中..." : `${questions.length} 道题`}</span>
            </div>
            <div className="table-scroll">
              <table className="question-table question-bank-table">
                <thead>
                  <tr>
                    <th style={{ width: 92 }}>编号</th>
                    <th style={{ width: 110 }}>题型</th>
                    <th style={{ width: 360 }}>题目</th>
                    <th style={{ width: 170 }}>一级维度</th>
                    <th style={{ width: 320 }}>二级维度</th>
                    <th style={{ width: 220 }}>能力</th>
                    <th style={{ width: 90 }}>难度</th>
                    <th style={{ width: 90 }}>状态</th>
                    <th style={{ width: 150 }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {questions.map((question) => (
                    <tr
                      key={question.id}
                      className={selected?.id === question.id ? "selected" : ""}
                      onClick={() => setSelected(question)}
                    >
                      <td>
                        <span className="badge">{question.itemCode}</span>
                      </td>
                      <td>{question.questionType || "单选"}</td>
                      <td className="title-cell">
                        <strong>{question.title}</strong>
                        <span>{question.scenario}</span>
                        <div className="badge-row">
                          {question.tags.slice(0, 3).map((tag) => (
                            <span className="badge" key={tag}>
                              {tag}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="taxonomy-cell">{question.dimension}</td>
                      <td className="taxonomy-cell">{question.secondaryDimension}</td>
                      <td className="taxonomy-cell">{question.subSkill}</td>
                      <td>{difficultyText(question.difficultyEstimate)}</td>
                      <td>
                        <span className={`badge status-${question.status}`}>{statusText(question.status)}</span>
                      </td>
                      <td>
                        <div className="actions">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              beginEdit(question);
                            }}
                          >
                            编辑
                          </button>
                          <button
                            className="danger"
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              void removeQuestion(question);
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
            {!loading && questions.length === 0 ? <div className="empty-state">暂无题目，可新增或导入 JSON。</div> : null}
          </section>

          <QuestionForm
            editing={editing}
            form={form}
            tagsText={tagsText}
            knowledgePointsText={knowledgePointsText}
            saving={saving}
            secondaryDimensions={formSecondaryDimensions}
            onSubmit={submitForm}
            onCancel={beginCreate}
            onTagsTextChange={setTagsText}
            onKnowledgePointsTextChange={setKnowledgePointsText}
            onFieldChange={updateField}
            onOptionChange={updateOption}
            onOptionAdd={addOption}
            onOptionRemove={removeOption}
          />
        </div>

        <QuestionDetail
          question={selected}
          onEdit={beginEdit}
          onDelete={(question) => {
            void removeQuestion(question);
          }}
        />
      </section>
        </>
      ) : null}
    </main>
  );
}

type QuestionFormProps = {
  editing: Question | null;
  form: QuestionInput;
  tagsText: string;
  knowledgePointsText: string;
  saving: boolean;
  secondaryDimensions: readonly string[];
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onTagsTextChange: (value: string) => void;
  onKnowledgePointsTextChange: (value: string) => void;
  onFieldChange: <K extends keyof QuestionInput>(field: K, value: QuestionInput[K]) => void;
  onOptionChange: (index: number, field: keyof QuestionOption, value: string) => void;
  onOptionAdd: () => void;
  onOptionRemove: (index: number) => void;
};

function QuestionForm({
  editing,
  form,
  tagsText,
  knowledgePointsText,
  saving,
  secondaryDimensions,
  onSubmit,
  onCancel,
  onTagsTextChange,
  onKnowledgePointsTextChange,
  onFieldChange,
  onOptionChange,
  onOptionAdd,
  onOptionRemove
}: QuestionFormProps) {
  return (
    <section className="form-panel">
      <div className="form-header">
        <h2>{editing ? "编辑题目" : "新增题目"}</h2>
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
            <span>题干</span>
            <textarea value={form.question} onChange={(event) => onFieldChange("question", event.target.value)} required />
          </label>
          <label className="form-row full">
            <span>场景</span>
            <textarea value={form.scenario} onChange={(event) => onFieldChange("scenario", event.target.value)} required />
          </label>
          <div className="form-row full">
            <label>选项</label>
            {form.options.map((option, index) => (
              <div className="option-editor" key={`${option.id}-${index}`}>
                <input
                  aria-label="选项编号"
                  value={option.id}
                  onChange={(event) => onOptionChange(index, "id", event.target.value)}
                  required
                />
                <input
                  aria-label="选项内容"
                  value={option.text}
                  onChange={(event) => onOptionChange(index, "text", event.target.value)}
                  required={index < 2}
                />
                <button type="button" onClick={() => onOptionRemove(index)} disabled={form.options.length <= 2}>
                  移除
                </button>
              </div>
            ))}
            <button type="button" onClick={onOptionAdd}>
              添加选项
            </button>
          </div>
          <label className="form-row">
            <span>题型</span>
            <select
              value={form.questionType || "单选"}
              onChange={(event) => onFieldChange("questionType", event.target.value)}
            >
              {questionTypeOptions.map((questionType) => (
                <option key={questionType} value={questionType}>
                  {questionType}
                </option>
              ))}
            </select>
          </label>
          <label className="form-row">
            <span>正确答案</span>
            <select
              value={form.correctAnswer}
              onChange={(event) => onFieldChange("correctAnswer", event.target.value)}
              required
            >
              {form.options.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.id || "未命名选项"}
                </option>
              ))}
            </select>
          </label>
          <label className="form-row">
            <span>状态</span>
            <select
              value={form.status}
              onChange={(event) => onFieldChange("status", event.target.value as QuestionStatus)}
            >
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {statusText(status)}
                </option>
              ))}
            </select>
          </label>
          <label className="form-row">
            <span>一级维度</span>
            <select
              value={form.dimension}
              onChange={(event) => onFieldChange("dimension", event.target.value)}
              required
            >
              <option value="">请选择一级维度</option>
              {aiLiteracyDimensions.map((dimension) => (
                <option key={dimension} value={dimension}>
                  {dimension}
                </option>
              ))}
            </select>
          </label>
          <label className="form-row">
            <span>二级维度</span>
            <select
              value={form.secondaryDimension}
              onChange={(event) => onFieldChange("secondaryDimension", event.target.value)}
              disabled={!form.dimension}
              required
            >
              <option value="">{form.dimension ? "请选择二级维度" : "先选一级维度"}</option>
              {secondaryDimensions.map((dimension) => (
                <option key={dimension} value={dimension}>
                  {dimension}
                </option>
              ))}
            </select>
          </label>
          <label className="form-row">
            <span>三级维度</span>
            <input
              value={form.tertiaryDimension || ""}
              onChange={(event) => onFieldChange("tertiaryDimension", event.target.value)}
            />
          </label>
          <label className="form-row">
            <span>四级维度</span>
            <input
              value={form.quaternaryDimension || ""}
              onChange={(event) => onFieldChange("quaternaryDimension", event.target.value)}
            />
          </label>
          <label className="form-row">
            <span>二级能力</span>
            <input value={form.subSkill} onChange={(event) => onFieldChange("subSkill", event.target.value)} required />
          </label>
          <label className="form-row">
            <span>认知层级</span>
            <select
              value={form.cognitiveLevel}
              onChange={(event) => onFieldChange("cognitiveLevel", event.target.value as CognitiveLevel)}
            >
              {cognitiveOptions.map((level) => (
                <option key={level} value={level}>
                  {cognitiveText(level)}
                </option>
              ))}
            </select>
          </label>
          <label className="form-row">
            <span>难度预估</span>
            <select
              value={form.difficultyEstimate}
              onChange={(event) => onFieldChange("difficultyEstimate", event.target.value as DifficultyEstimate)}
            >
              {difficultyOptions.map((difficulty) => (
                <option key={difficulty} value={difficulty}>
                  {difficultyText(difficulty)}
                </option>
              ))}
            </select>
          </label>
          <label className="form-row full">
            <span>标签，用英文逗号分隔</span>
            <input value={tagsText} onChange={(event) => onTagsTextChange(event.target.value)} />
          </label>
          <label className="form-row full">
            <span>知识点，用英文逗号分隔</span>
            <input value={knowledgePointsText} onChange={(event) => onKnowledgePointsTextChange(event.target.value)} />
          </label>
          <label className="form-row full">
            <span>解析</span>
            <textarea
              value={form.explanation}
              onChange={(event) => onFieldChange("explanation", event.target.value)}
              required
            />
          </label>
          <label className="form-row full">
            <span>来源</span>
            <input
              value={form.sourceReference}
              onChange={(event) => onFieldChange("sourceReference", event.target.value)}
              required
            />
          </label>
        </div>
        <div className="toolbar" style={{ marginTop: 14 }}>
          <button className="primary" type="submit" disabled={saving}>
            {saving ? "保存中..." : editing ? "保存修改" : "创建题目"}
          </button>
          <button type="button" onClick={onCancel}>
            重置表单
          </button>
        </div>
      </form>
    </section>
  );
}

type QuestionDetailProps = {
  question: Question | null;
  onEdit: (question: Question) => void;
  onDelete: (question: Question) => void;
};

function QuestionDetail({ question, onEdit, onDelete }: QuestionDetailProps) {
  if (!question) {
    return (
      <aside className="detail-panel">
        <div className="detail-header">
          <h2>题目详情</h2>
        </div>
        <div className="empty-state">选择一条题目查看详情。</div>
      </aside>
    );
  }

  return (
    <aside className="detail-panel">
      <div className="detail-header">
        <h2>题目详情</h2>
        <div className="actions">
          <button type="button" onClick={() => onEdit(question)}>
            编辑
          </button>
          <button className="danger" type="button" onClick={() => onDelete(question)}>
            删除
          </button>
        </div>
      </div>
      <div className="detail-body">
        <span className="badge">{question.itemCode}</span>
        <h3>{question.title}</h3>
        <p>{question.question}</p>

        <h3>场景</h3>
        <p>{question.scenario}</p>

        <h3>选项</h3>
        <ul className="option-list">
          {question.options.map((option) => (
            <li key={option.id} className={option.id === question.correctAnswer ? "correct" : ""}>
              <strong>{option.id}.</strong> {option.text}
            </li>
          ))}
        </ul>

        <h3>解析</h3>
        <p>{question.explanation}</p>

        <div className="badge-row">
          <span className="badge">{question.questionType || "单选"}</span>
          <span className="badge">{question.dimension}</span>
          <span className="badge">{question.secondaryDimension}</span>
          {question.tertiaryDimension ? <span className="badge">{question.tertiaryDimension}</span> : null}
          {question.quaternaryDimension ? <span className="badge">{question.quaternaryDimension}</span> : null}
          <span className="badge">{question.subSkill}</span>
          <span className="badge">{cognitiveText(question.cognitiveLevel)}</span>
          <span className="badge">{difficultyText(question.difficultyEstimate)}</span>
          <span className={`badge status-${question.status}`}>{statusText(question.status)}</span>
        </div>

        <h3>标签</h3>
        <div className="badge-row">
          {question.tags.length > 0 ? question.tags.map((tag) => <span className="badge" key={tag}>{tag}</span>) : "无"}
        </div>

        <h3>知识点</h3>
        <div className="badge-row">
          {question.knowledgePoints && question.knowledgePoints.length > 0
            ? question.knowledgePoints.map((point) => <span className="badge" key={point}>{point}</span>)
            : "无"}
        </div>

        <h3>来源</h3>
        <p>{question.sourceReference}</p>
        <p className="muted">创建：{new Date(question.createdAt).toLocaleString()}</p>
        <p className="muted">更新：{new Date(question.updatedAt).toLocaleString()}</p>
      </div>
    </aside>
  );
}
