"use client";

import { useEffect, useMemo, useState } from "react";
import PipelineGeneratorPanel from "@/components/PipelineGeneratorPanel";
import { aiLiteracyDimensions, getSecondaryDimensions } from "@/lib/aiLiteracyFramework";
import { GenerationBatch, GenerationJob, QuestionDraft, QuestionDraftInput } from "@/types/draft";
import { CognitiveLevel, DifficultyEstimate, KnowledgePoint, QuestionOption, QuestionStatus, QuestionType } from "@/types/question";

const cognitiveOptions: CognitiveLevel[] = ["remember", "understand", "apply", "analyze", "evaluate", "create"];
const difficultyOptions: DifficultyEstimate[] = ["easy", "medium", "hard"];
const statusOptions: QuestionStatus[] = ["draft", "reviewed", "tested", "retired"];
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

function jobStatusText(status: string) {
  const map: Record<string, string> = {
    running: "生成中",
    completed: "已完成",
    partial: "部分完成",
    failed: "失败"
  };
  return map[status] ?? status;
}

function toDraftInput(draft: QuestionDraft): QuestionDraftInput {
  return {
    questionType: draft.questionType || "单选",
    title: draft.title,
    question: draft.question,
    scenario: draft.scenario,
    options: draft.options,
    correctAnswer: draft.correctAnswer,
    explanation: draft.explanation,
    dimension: draft.dimension,
    secondaryDimension: draft.secondaryDimension,
    tertiaryDimension: draft.tertiaryDimension || "",
    quaternaryDimension: draft.quaternaryDimension || "",
    subSkill: draft.subSkill,
    cognitiveLevel: draft.cognitiveLevel,
    difficultyEstimate: draft.difficultyEstimate,
    tags: draft.tags,
    knowledgePoints: draft.knowledgePoints || [],
    sourceReference: draft.sourceReference,
    status: draft.status,
    sourceKnowledgeIds: draft.sourceKnowledgeIds,
    generationRequirement: draft.generationRequirement
  };
}

export default function DraftGeneratorPanel() {
  const [drafts, setDrafts] = useState<QuestionDraft[]>([]);
  const [knowledgePoints, setKnowledgePoints] = useState<KnowledgePoint[]>([]);
  const [generationJobs, setGenerationJobs] = useState<GenerationJob[]>([]);
  const [generationBatches, setGenerationBatches] = useState<GenerationBatch[]>([]);
  const [tagsTextById, setTagsTextById] = useState<Record<string, string>>({});
  const [knowledgePointsTextById, setKnowledgePointsTextById] = useState<Record<string, string>>({});
  const [expandedDraftId, setExpandedDraftId] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState("");
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const [knowledgePointsResponse, draftResponse, jobsResponse, batchesResponse] = await Promise.all([
        fetch("/api/knowledge-points", { cache: "no-store" }),
        fetch("/api/drafts", { cache: "no-store" }),
        fetch("/api/generation-jobs", { cache: "no-store" }),
        fetch("/api/generation-batches", { cache: "no-store" })
      ]);

      if (!knowledgePointsResponse.ok || !draftResponse.ok || !jobsResponse.ok || !batchesResponse.ok) {
        throw new Error("数据加载失败");
      }

      const [knowledgePointsData, draftData, jobsData, batchesData] = (await Promise.all([
        knowledgePointsResponse.json(),
        draftResponse.json(),
        jobsResponse.json(),
        batchesResponse.json()
      ])) as [KnowledgePoint[], QuestionDraft[], GenerationJob[], GenerationBatch[]];

      setKnowledgePoints(knowledgePointsData);
      setDrafts(draftData);
      setGenerationJobs(jobsData);
      setGenerationBatches(batchesData);
      setTagsTextById(Object.fromEntries(draftData.map((draft) => [draft.id, draft.tags.join(", ")])));
      setKnowledgePointsTextById(
        Object.fromEntries(draftData.map((draft) => [draft.id, (draft.knowledgePoints || []).join(", ")]))
      );
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const dimensionOptions = useMemo(() => {
    const values = Array.from(new Set(knowledgePoints.map((point) => point.primaryDimension).filter(Boolean)));
    return values.sort((a, b) => {
      const aIndex = aiLiteracyDimensions.indexOf(a as (typeof aiLiteracyDimensions)[number]);
      const bIndex = aiLiteracyDimensions.indexOf(b as (typeof aiLiteracyDimensions)[number]);
      if (aIndex === -1 && bIndex === -1) {
        return a.localeCompare(b, "zh-Hans-CN");
      }
      if (aIndex === -1) {
        return 1;
      }
      if (bIndex === -1) {
        return -1;
      }
      return aIndex - bIndex;
    });
  }, [knowledgePoints]);

  const secondaryOptionsByDimension = useMemo(() => {
    const grouped = new Map<string, string[]>();
    knowledgePoints.forEach((point) => {
      if (!point.primaryDimension || !point.secondaryDimension) {
        return;
      }
      const current = grouped.get(point.primaryDimension) ?? [];
      if (!current.includes(point.secondaryDimension)) {
        current.push(point.secondaryDimension);
      }
      grouped.set(point.primaryDimension, current);
    });
    grouped.forEach((items) => items.sort((a, b) => a.localeCompare(b, "zh-Hans-CN")));
    return grouped;
  }, [knowledgePoints]);

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
              ...(field === "dimension"
                ? { secondaryDimension: "", tertiaryDimension: "", quaternaryDimension: "", knowledgePoints: [] }
                : {}),
              ...(field === "secondaryDimension" ? { tertiaryDimension: "", quaternaryDimension: "", knowledgePoints: [] } : {}),
              ...(field === "tertiaryDimension" ? { quaternaryDimension: "", knowledgePoints: [] } : {})
            }
          : draft
      )
    );
    if (field === "dimension" || field === "secondaryDimension" || field === "tertiaryDimension") {
      setKnowledgePointsTextById((current) => ({ ...current, [id]: "" }));
    }
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
        .filter(Boolean),
      knowledgePoints: (knowledgePointsTextById[draft.id] ?? "")
        .split(",")
        .map((point) => point.trim())
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
          <p>基于后端知识点流水线生成题目草稿，人工确认后进入正式题库。</p>
        </div>
      </section>

      {error ? <div className="error-box">{error}</div> : null}
      {statusMessage ? <div className="status-box">{statusMessage}</div> : null}

      <PipelineGeneratorPanel onCompleted={loadData} />

      <GenerationJobList jobs={generationJobs} batches={generationBatches} loading={loading} />

      <section className="panel draft-list">
        <div className="panel-header">
          <h2>草稿列表</h2>
          <span className="muted">{drafts.length} 道草稿</span>
        </div>
        <div className="draft-card-list">
          {drafts.map((draft) =>
            expandedDraftId === draft.id ? (
              <DraftEditor
                key={draft.id}
                draft={draft}
                tagsText={tagsTextById[draft.id] ?? ""}
                knowledgePointsText={knowledgePointsTextById[draft.id] ?? ""}
                dimensionOptions={dimensionOptions}
                getSecondaryOptions={(dimension) =>
                  secondaryOptionsByDimension.get(dimension) ?? [...getSecondaryDimensions(dimension)]
                }
                saving={savingId === draft.id}
                onCollapse={() => setExpandedDraftId("")}
                onFieldChange={updateDraftField}
                onTagsTextChange={(value) =>
                  setTagsTextById((current) => ({
                    ...current,
                    [draft.id]: value
                  }))
                }
                onKnowledgePointsTextChange={(value) =>
                  setKnowledgePointsTextById((current) => ({
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
            ) : (
              <DraftSummaryCard
                key={draft.id}
                draft={draft}
                saving={savingId === draft.id}
                onEdit={() => setExpandedDraftId(draft.id)}
                onDelete={() => void deleteDraft(draft)}
                onAccept={() => void acceptDraft(draft)}
              />
            )
          )}
          {!loading && drafts.length === 0 ? <div className="empty-state">暂无出题草稿。</div> : null}
        </div>
      </section>
    </>
  );
}

type GenerationJobListProps = {
  jobs: GenerationJob[];
  batches: GenerationBatch[];
  loading: boolean;
};

function GenerationJobList({ jobs, batches, loading }: GenerationJobListProps) {
  const batchesByJob = useMemo(() => {
    const grouped = new Map<string, GenerationBatch[]>();
    batches.forEach((batch) => {
      const current = grouped.get(batch.jobId) ?? [];
      current.push(batch);
      grouped.set(batch.jobId, current);
    });
    grouped.forEach((items) => items.sort((a, b) => a.batchIndex - b.batchIndex));
    return grouped;
  }, [batches]);

  return (
    <section className="panel generation-job-list">
      <div className="panel-header">
        <h2>生成任务记录</h2>
        <span className="muted">{loading ? "加载中..." : `${jobs.length} 次任务`}</span>
      </div>
      <div className="job-list">
        {jobs.map((job) => (
          <article className="job-item" key={job.id}>
            <div className="job-item-main">
              <div className="badge-row">
                <span className={`badge job-status-${job.status}`}>{jobStatusText(job.status)}</span>
                <span className="badge">{job.provider}</span>
                <span className="badge">{job.model}</span>
                <span className="badge">目标 {job.count} 道</span>
                <span className="badge">草稿 {job.draftCount} 道</span>
                <span className="badge">
                  批次 {job.completedBatchCount}/{job.batchCount}
                </span>
                {job.failedBatchCount > 0 ? <span className="badge job-status-failed">失败 {job.failedBatchCount}</span> : null}
              </div>
              <p>{job.requirement || "未填写额外出题要求"}</p>
              <div className="badge-row">
                {job.targetDimensions.map((dimension, index) => (
                  <span className="badge" key={`${dimension}-${index}`}>
                    {dimension}
                  </span>
                ))}
                {job.targetSecondaryDimensions.map((dimension, index) => (
                  <span className="badge" key={`${dimension}-${index}`}>
                    {dimension}
                  </span>
                ))}
                {job.targetTags.map((tag, index) => (
                  <span className="badge" key={`${tag}-${index}`}>
                    {tag}
                  </span>
                ))}
              </div>
              {job.error ? <p className="job-error">{job.error}</p> : null}
              <div className="batch-list">
                {(batchesByJob.get(job.id) ?? []).map((batch) => (
                  <div className="batch-item" key={batch.id}>
                    <span className={`badge job-status-${batch.status}`}>
                      第 {batch.batchIndex} 批 · {jobStatusText(batch.status)}
                    </span>
                    <span className="muted">
                      {batch.generatedCount}/{batch.plannedCount} 道 · {batch.model}
                    </span>
                    {batch.error ? <span className="batch-error">{batch.error}</span> : null}
                  </div>
                ))}
              </div>
            </div>
            <div className="job-time">
              <span>{new Date(job.createdAt).toLocaleString()}</span>
              {job.completedAt ? <span>{new Date(job.completedAt).toLocaleString()}</span> : null}
            </div>
          </article>
        ))}
        {!loading && jobs.length === 0 ? <div className="empty-state">暂无生成任务记录。</div> : null}
      </div>
    </section>
  );
}

type DraftSummaryCardProps = {
  draft: QuestionDraft;
  saving: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onAccept: () => void;
};

function DraftSummaryCard({ draft, saving, onEdit, onDelete, onAccept }: DraftSummaryCardProps) {
  const summaryText = [draft.scenario, draft.question].filter(Boolean).join(" ");
  const knowledgePoints = draft.knowledgePoints?.length ? draft.knowledgePoints : draft.tags;

  return (
    <article className="draft-card draft-summary-card">
      <div className="draft-card-header">
        <div>
          <strong>{draft.title || "未命名草稿"}</strong>
          <p className="muted">{summaryText.length > 140 ? `${summaryText.slice(0, 140)}...` : summaryText}</p>
        </div>
        <div className="actions">
          <button type="button" onClick={onEdit} disabled={saving}>
            编辑
          </button>
          <button className="danger" type="button" onClick={onDelete} disabled={saving}>
            删除
          </button>
          <button className="primary" type="button" onClick={onAccept} disabled={saving}>
            接受
          </button>
        </div>
      </div>
      <div className="badge-row">
        <span className="badge">{draft.questionType || "单选"}</span>
        <span className="badge">{draft.dimension || "未标一级维度"}</span>
        <span className="badge">{draft.secondaryDimension || "未标二级维度"}</span>
        <span className="badge">{difficultyText(draft.difficultyEstimate)}</span>
        <span className="badge">{statusText(draft.status)}</span>
      </div>
      {knowledgePoints.length > 0 ? (
        <div className="badge-row">
          {knowledgePoints.slice(0, 6).map((item, index) => (
            <span className="badge" key={`${draft.id}-${item}-${index}`}>
              {item}
            </span>
          ))}
        </div>
      ) : null}
    </article>
  );
}

type DraftEditorProps = {
  draft: QuestionDraft;
  tagsText: string;
  knowledgePointsText: string;
  dimensionOptions: string[];
  getSecondaryOptions: (dimension: string) => string[];
  saving: boolean;
  onCollapse: () => void;
  onFieldChange: <K extends keyof QuestionDraftInput>(id: string, field: K, value: QuestionDraftInput[K]) => void;
  onTagsTextChange: (value: string) => void;
  onKnowledgePointsTextChange: (value: string) => void;
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
  knowledgePointsText,
  dimensionOptions,
  getSecondaryOptions,
  saving,
  onCollapse,
  onFieldChange,
  onTagsTextChange,
  onKnowledgePointsTextChange,
  onOptionChange,
  onOptionAdd,
  onOptionRemove,
  onSave,
  onDelete,
  onAccept
}: DraftEditorProps) {
  const secondaryDimensionOptions = useMemo(() => {
    const options = getSecondaryOptions(draft.dimension);
    if (draft.secondaryDimension && !options.includes(draft.secondaryDimension)) {
      return [draft.secondaryDimension, ...options];
    }
    return options;
  }, [draft.dimension, draft.secondaryDimension, getSecondaryOptions]);

  return (
    <article className="draft-card">
      <div className="draft-card-header">
        <div>
          <strong>{draft.title}</strong>
          <p className="muted">草稿题未分配 itemCode，接受后进入正式题库时自动分配。</p>
        </div>
        <div className="actions">
          <button type="button" onClick={onCollapse} disabled={saving}>
            收起
          </button>
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
          <span>题型</span>
          <select
            value={draft.questionType || "单选"}
            onChange={(event) => onFieldChange(draft.id, "questionType", event.target.value)}
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
            {dimensionOptions.map((dimension) => (
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
            {secondaryDimensionOptions.map((dimension) => (
              <option key={dimension} value={dimension}>
                {dimension}
              </option>
            ))}
          </select>
        </label>
        <label className="form-row">
          <span>三级维度</span>
          <input
            value={draft.tertiaryDimension || ""}
            onChange={(event) => onFieldChange(draft.id, "tertiaryDimension", event.target.value)}
          />
        </label>
        <label className="form-row">
          <span>四级维度</span>
          <input
            value={draft.quaternaryDimension || ""}
            onChange={(event) => onFieldChange(draft.id, "quaternaryDimension", event.target.value)}
          />
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
          <span>知识点，用英文逗号分隔</span>
          <input value={knowledgePointsText} onChange={(event) => onKnowledgePointsTextChange(event.target.value)} />
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
