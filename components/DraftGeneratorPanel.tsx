"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { aiLiteracyDimensions, getSecondaryDimensions } from "@/lib/aiLiteracyFramework";
import { KnowledgeEntry } from "@/types/knowledge";
import { QuestionDraft, QuestionDraftInput } from "@/types/draft";
import { CognitiveLevel, DifficultyEstimate, QuestionOption, QuestionStatus } from "@/types/question";

const cognitiveOptions: CognitiveLevel[] = ["remember", "understand", "apply", "analyze", "evaluate", "create"];
const difficultyOptions: DifficultyEstimate[] = ["easy", "medium", "hard"];
const statusOptions: QuestionStatus[] = ["draft", "reviewed", "tested", "retired"];

function toggleValue(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
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

function difficultyText(difficulty: DifficultyEstimate) {
  const map: Record<DifficultyEstimate, string> = {
    easy: "简单",
    medium: "中等",
    hard: "困难"
  };
  return map[difficulty];
}

function statusText(status: QuestionStatus) {
  const map: Record<QuestionStatus, string> = {
    draft: "草稿",
    reviewed: "已审",
    tested: "已测",
    retired: "停用"
  };
  return map[status];
}

function toDraftInput(draft: QuestionDraft): QuestionDraftInput {
  return {
    title: draft.title,
    question: draft.question,
    scenario: draft.scenario,
    options: draft.options,
    correctAnswer: draft.correctAnswer,
    explanation: draft.explanation,
    dimension: draft.dimension,
    secondaryDimension: draft.secondaryDimension,
    subSkill: draft.subSkill,
    cognitiveLevel: draft.cognitiveLevel,
    difficultyEstimate: draft.difficultyEstimate,
    tags: draft.tags,
    sourceReference: draft.sourceReference,
    status: draft.status,
    sourceKnowledgeIds: draft.sourceKnowledgeIds,
    generationRequirement: draft.generationRequirement
  };
}

export default function DraftGeneratorPanel() {
  const [knowledgeEntries, setKnowledgeEntries] = useState<KnowledgeEntry[]>([]);
  const [selectedKnowledgeIds, setSelectedKnowledgeIds] = useState<string[]>([]);
  const [selectedDimensions, setSelectedDimensions] = useState<string[]>([]);
  const [selectedSecondaryDimensions, setSelectedSecondaryDimensions] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [requirement, setRequirement] = useState("");
  const [drafts, setDrafts] = useState<QuestionDraft[]>([]);
  const [tagsTextById, setTagsTextById] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [savingId, setSavingId] = useState("");
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const [knowledgeResponse, draftResponse] = await Promise.all([
        fetch("/api/knowledge", { cache: "no-store" }),
        fetch("/api/drafts", { cache: "no-store" })
      ]);

      if (!knowledgeResponse.ok || !draftResponse.ok) {
        throw new Error("数据加载失败");
      }

      const [knowledgeData, draftData] = (await Promise.all([
        knowledgeResponse.json(),
        draftResponse.json()
      ])) as [KnowledgeEntry[], QuestionDraft[]];

      setKnowledgeEntries(knowledgeData);
      setDrafts(draftData);
      setTagsTextById(Object.fromEntries(draftData.map((draft) => [draft.id, draft.tags.join(", ")])));
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const selectedKnowledgeEntries = useMemo(
    () => knowledgeEntries.filter((entry) => selectedKnowledgeIds.includes(entry.id)),
    [knowledgeEntries, selectedKnowledgeIds]
  );

  const availableSecondaryDimensions = useMemo(
    () => selectedDimensions.flatMap((dimension) => getSecondaryDimensions(dimension)),
    [selectedDimensions]
  );

  const availableTags = useMemo(
    () =>
      Array.from(
        new Set(selectedKnowledgeEntries.flatMap((entry) => entry.tags).map((tag) => tag.trim()).filter(Boolean))
      ).sort(),
    [selectedKnowledgeEntries]
  );

  useEffect(() => {
    setSelectedSecondaryDimensions((current) =>
      current.filter((dimension) => availableSecondaryDimensions.some((item) => item === dimension))
    );
  }, [availableSecondaryDimensions]);

  useEffect(() => {
    setSelectedTags((current) => current.filter((tag) => availableTags.includes(tag)));
  }, [availableTags]);

  function toggleKnowledge(id: string) {
    setSelectedKnowledgeIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id]
    );
  }

  async function generateDrafts(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedKnowledgeIds.length === 0) {
      setError("请先选择至少一个知识条目");
      return;
    }

    setGenerating(true);
    setError("");
    setStatusMessage("");

    try {
      const response = await fetch("/api/drafts/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          knowledgeIds: selectedKnowledgeIds,
          requirement,
          targetDimensions: selectedDimensions,
          targetSecondaryDimensions: selectedSecondaryDimensions,
          targetTags: selectedTags
        })
      });
      const result = (await response.json()) as QuestionDraft[] | { error?: string };
      if (!response.ok) {
        throw new Error("error" in result ? result.error : "生成失败");
      }

      await loadData();
      setStatusMessage(`生成完成：新增 ${(result as QuestionDraft[]).length} 道草稿`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  function updateDraftField<K extends keyof QuestionDraftInput>(
    id: string,
    field: K,
    value: QuestionDraftInput[K]
  ) {
    setDrafts((current) =>
      current.map((draft) =>
        draft.id === id
          ? {
              ...draft,
              [field]: value,
              ...(field === "dimension" ? { secondaryDimension: "" } : {})
            }
          : draft
      )
    );
  }

  function updateOption(draftId: string, optionIndex: number, field: keyof QuestionOption, value: string) {
    setDrafts((current) =>
      current.map((draft) =>
        draft.id === draftId
          ? {
              ...draft,
              options: draft.options.map((option, index) =>
                index === optionIndex ? { ...option, [field]: value } : option
              )
            }
          : draft
      )
    );
  }

  function addOption(draftId: string) {
    setDrafts((current) =>
      current.map((draft) =>
        draft.id === draftId
          ? {
              ...draft,
              options: [...draft.options, { id: String.fromCharCode(65 + draft.options.length), text: "" }]
            }
          : draft
      )
    );
  }

  function removeOption(draftId: string, optionIndex: number) {
    setDrafts((current) =>
      current.map((draft) => {
        if (draft.id !== draftId || draft.options.length <= 2) {
          return draft;
        }

        const options = draft.options.filter((_, index) => index !== optionIndex);
        return {
          ...draft,
          options,
          correctAnswer: options.some((option) => option.id === draft.correctAnswer)
            ? draft.correctAnswer
            : options[0]?.id ?? ""
        };
      })
    );
  }

  async function saveDraft(draft: QuestionDraft) {
    setSavingId(draft.id);
    setError("");
    setStatusMessage("");

    const payload: QuestionDraftInput = {
      ...toDraftInput(draft),
      options: draft.options
        .map((option) => ({ id: option.id.trim(), text: option.text.trim() }))
        .filter((option) => option.id && option.text),
      tags: (tagsTextById[draft.id] ?? "")
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean)
    };

    try {
      const response = await fetch(`/api/drafts/${draft.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = (await response.json()) as QuestionDraft | { error?: string };
      if (!response.ok) {
        throw new Error("error" in result ? result.error : "保存失败");
      }

      await loadData();
      setStatusMessage("草稿已保存");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "保存失败");
    } finally {
      setSavingId("");
    }
  }

  async function deleteDraft(draft: QuestionDraft) {
    const confirmed = window.confirm(`确定删除草稿「${draft.title}」吗？`);
    if (!confirmed) {
      return;
    }

    setError("");
    setStatusMessage("");
    const response = await fetch(`/api/drafts/${draft.id}`, { method: "DELETE" });
    if (!response.ok) {
      setError("删除失败");
      return;
    }

    await loadData();
    setStatusMessage("草稿已删除");
  }

  async function acceptDraft(draft: QuestionDraft) {
    setSavingId(draft.id);
    setError("");
    setStatusMessage("");

    try {
      await saveDraft(draft);
      const response = await fetch(`/api/drafts/${draft.id}/accept`, { method: "POST" });
      const result = (await response.json()) as { itemCode?: string; title?: string; error?: string };
      if (!response.ok) {
        throw new Error(result.error || "接受失败");
      }

      await loadData();
      setStatusMessage(`已进入正式题库：${result.itemCode} ${result.title}`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "接受失败");
    } finally {
      setSavingId("");
    }
  }

  return (
    <>
      <section className="section-heading">
        <div>
          <h2>出题草稿</h2>
          <p>基于知识条目生成 mock 题目草稿，人工确认后进入正式题库。</p>
        </div>
      </section>

      {error ? <div className="error-box">{error}</div> : null}
      {statusMessage ? <div className="status-box">{statusMessage}</div> : null}

      <section className="panel draft-generator">
        <div className="panel-header">
          <h2>生成草稿</h2>
          <span className="muted">{loading ? "加载中..." : `${knowledgeEntries.length} 条知识可选`}</span>
        </div>
        <form className="form-body" onSubmit={generateDrafts}>
          <div className="knowledge-picker">
            {knowledgeEntries.length === 0 ? (
              <div className="empty-state">暂无知识条目，请先到知识库新增或导入。</div>
            ) : (
              knowledgeEntries.map((entry) => (
                <label className="knowledge-choice" key={entry.id}>
                  <input
                    type="checkbox"
                    checked={selectedKnowledgeIds.includes(entry.id)}
                    onChange={() => toggleKnowledge(entry.id)}
                  />
                  <span>
                    <strong>{entry.title}</strong>
                    <small>{entry.sourceType} · {entry.sourceFileName}</small>
                  </span>
                </label>
              ))
            )}
          </div>
          <div className="criteria-section">
            <div className="criteria-block">
              <label>一级维度</label>
              <div className="choice-grid">
                {aiLiteracyDimensions.map((dimension) => (
                  <label className="filter-choice" key={dimension}>
                    <input
                      type="checkbox"
                      checked={selectedDimensions.includes(dimension)}
                      onChange={() => setSelectedDimensions((current) => toggleValue(current, dimension))}
                    />
                    <span>{dimension}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="criteria-block">
              <label>二级维度</label>
              {selectedDimensions.length === 0 ? (
                <p className="muted">先选择一级维度后，可勾选对应二级维度。</p>
              ) : (
                <div className="choice-grid secondary-choice-grid">
                  {availableSecondaryDimensions.map((dimension) => (
                    <label className="filter-choice" key={dimension}>
                      <input
                        type="checkbox"
                        checked={selectedSecondaryDimensions.includes(dimension)}
                        onChange={() =>
                          setSelectedSecondaryDimensions((current) => toggleValue(current, dimension))
                        }
                      />
                      <span>{dimension}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="criteria-block">
              <label>知识点标签</label>
              {selectedKnowledgeIds.length === 0 ? (
                <p className="muted">先选择知识条目后，可按标签进一步聚焦出题。</p>
              ) : availableTags.length === 0 ? (
                <p className="muted">所选知识条目暂无标签，可先到知识库编辑标签。</p>
              ) : (
                <div className="choice-grid">
                  {availableTags.map((tag) => (
                    <label className="filter-choice" key={tag}>
                      <input
                        type="checkbox"
                        checked={selectedTags.includes(tag)}
                        onChange={() => setSelectedTags((current) => toggleValue(current, tag))}
                      />
                      <span>{tag}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
          <label className="form-row full">
            <span>出题要求</span>
            <textarea
              value={requirement}
              onChange={(event) => setRequirement(event.target.value)}
              placeholder="例如：生成 3 道场景化单选题，偏应用层级，聚焦隐私风险和结果核验。"
            />
          </label>
          <div className="toolbar" style={{ marginTop: 14 }}>
            <button className="primary" type="submit" disabled={generating || selectedKnowledgeIds.length === 0}>
              {generating ? "生成中..." : "生成题目草稿"}
            </button>
          </div>
        </form>
      </section>

      <section className="panel draft-list">
        <div className="panel-header">
          <h2>草稿列表</h2>
          <span className="muted">{drafts.length} 道草稿</span>
        </div>
        <div className="draft-card-list">
          {drafts.map((draft) => (
            <DraftEditor
              key={draft.id}
              draft={draft}
              tagsText={tagsTextById[draft.id] ?? ""}
              saving={savingId === draft.id}
              onFieldChange={updateDraftField}
              onTagsTextChange={(value) =>
                setTagsTextById((current) => ({
                  ...current,
                  [draft.id]: value
                }))
              }
              onOptionChange={updateOption}
              onOptionAdd={addOption}
              onOptionRemove={removeOption}
              onSave={() => void saveDraft(draft)}
              onDelete={() => void deleteDraft(draft)}
              onAccept={() => void acceptDraft(draft)}
            />
          ))}
          {!loading && drafts.length === 0 ? <div className="empty-state">暂无出题草稿。</div> : null}
        </div>
      </section>
    </>
  );
}

type DraftEditorProps = {
  draft: QuestionDraft;
  tagsText: string;
  saving: boolean;
  onFieldChange: <K extends keyof QuestionDraftInput>(id: string, field: K, value: QuestionDraftInput[K]) => void;
  onTagsTextChange: (value: string) => void;
  onOptionChange: (draftId: string, optionIndex: number, field: keyof QuestionOption, value: string) => void;
  onOptionAdd: (draftId: string) => void;
  onOptionRemove: (draftId: string, optionIndex: number) => void;
  onSave: () => void;
  onDelete: () => void;
  onAccept: () => void;
};

function DraftEditor({
  draft,
  tagsText,
  saving,
  onFieldChange,
  onTagsTextChange,
  onOptionChange,
  onOptionAdd,
  onOptionRemove,
  onSave,
  onDelete,
  onAccept
}: DraftEditorProps) {
  return (
    <article className="draft-card">
      <div className="draft-card-header">
        <div>
          <strong>{draft.title}</strong>
          <p className="muted">草稿题未分配 itemCode，接受后进入正式题库时自动分配。</p>
        </div>
        <div className="actions">
          <button type="button" onClick={onSave} disabled={saving}>
            {saving ? "处理中..." : "保存"}
          </button>
          <button className="danger" type="button" onClick={onDelete} disabled={saving}>
            删除
          </button>
          <button className="primary" type="button" onClick={onAccept} disabled={saving}>
            接受
          </button>
        </div>
      </div>
      <div className="form-grid">
        <label className="form-row full">
          <span>标题</span>
          <input value={draft.title} onChange={(event) => onFieldChange(draft.id, "title", event.target.value)} />
        </label>
        <label className="form-row full">
          <span>题干</span>
          <textarea value={draft.question} onChange={(event) => onFieldChange(draft.id, "question", event.target.value)} />
        </label>
        <label className="form-row full">
          <span>场景</span>
          <textarea value={draft.scenario} onChange={(event) => onFieldChange(draft.id, "scenario", event.target.value)} />
        </label>
        <div className="form-row full">
          <label>选项</label>
          {draft.options.map((option, index) => (
            <div className="option-editor" key={`${draft.id}-${index}`}>
              <input value={option.id} onChange={(event) => onOptionChange(draft.id, index, "id", event.target.value)} />
              <input value={option.text} onChange={(event) => onOptionChange(draft.id, index, "text", event.target.value)} />
              <button type="button" onClick={() => onOptionRemove(draft.id, index)} disabled={draft.options.length <= 2}>
                移除
              </button>
            </div>
          ))}
          <button type="button" onClick={() => onOptionAdd(draft.id)}>
            添加选项
          </button>
        </div>
        <label className="form-row">
          <span>正确答案</span>
          <select value={draft.correctAnswer} onChange={(event) => onFieldChange(draft.id, "correctAnswer", event.target.value)}>
            {draft.options.map((option) => (
              <option key={option.id} value={option.id}>
                {option.id || "未命名选项"}
              </option>
            ))}
          </select>
        </label>
        <label className="form-row">
          <span>状态</span>
          <select value={draft.status} onChange={(event) => onFieldChange(draft.id, "status", event.target.value as QuestionStatus)}>
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
            value={draft.dimension}
            onChange={(event) => onFieldChange(draft.id, "dimension", event.target.value)}
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
            value={draft.secondaryDimension}
            onChange={(event) => onFieldChange(draft.id, "secondaryDimension", event.target.value)}
            disabled={!draft.dimension}
          >
            <option value="">{draft.dimension ? "请选择二级维度" : "先选一级维度"}</option>
            {getSecondaryDimensions(draft.dimension).map((dimension) => (
              <option key={dimension} value={dimension}>
                {dimension}
              </option>
            ))}
          </select>
        </label>
        <label className="form-row">
          <span>二级能力</span>
          <input value={draft.subSkill} onChange={(event) => onFieldChange(draft.id, "subSkill", event.target.value)} />
        </label>
        <label className="form-row">
          <span>认知层级</span>
          <select value={draft.cognitiveLevel} onChange={(event) => onFieldChange(draft.id, "cognitiveLevel", event.target.value as CognitiveLevel)}>
            {cognitiveOptions.map((level) => (
              <option key={level} value={level}>
                {cognitiveText(level)}
              </option>
            ))}
          </select>
        </label>
        <label className="form-row">
          <span>难度预估</span>
          <select value={draft.difficultyEstimate} onChange={(event) => onFieldChange(draft.id, "difficultyEstimate", event.target.value as DifficultyEstimate)}>
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
          <span>解析</span>
          <textarea value={draft.explanation} onChange={(event) => onFieldChange(draft.id, "explanation", event.target.value)} />
        </label>
        <label className="form-row full">
          <span>来源</span>
          <input value={draft.sourceReference} onChange={(event) => onFieldChange(draft.id, "sourceReference", event.target.value)} />
        </label>
      </div>
    </article>
  );
}
