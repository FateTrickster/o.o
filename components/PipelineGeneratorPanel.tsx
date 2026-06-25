"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { aiLiteracyDimensions, getSecondaryDimensions } from "@/lib/aiLiteracyFramework";
import { KnowledgePoint } from "@/types/question";

type PipelineResultCandidate = {
  index: number;
  draftId?: string;
  provider: string;
  passed: boolean;
  knowledgeCode: string;
  primaryDimension: string;
  secondaryDimension: string;
  knowledgePoint: string;
  title: string;
  scenario: string;
  question: string;
  correctAnswer: string;
  structureResult: string;
  qualityLevel: string;
  duplicateScore: number;
  duplicateWith?: string;
  tags: string;
};

type PipelineResult = {
  selectedKnowledgePoints: number;
  generatedCandidates: number;
  createdDrafts: number;
  errors: string[];
  reportJson: string;
  reportCsv: string;
  candidates: PipelineResultCandidate[];
};

type PipelineGeneratorPanelProps = {
  onCompleted: () => Promise<void> | void;
};

const providerOptions = ["mock", "xfyun", "deepseek"];
const difficultyOptions = ["easy", "medium", "hard"];
const cognitiveOptions = ["", "remember", "understand", "apply", "analyze", "evaluate", "create"];

function toggleValue(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function splitCodes(value: string) {
  return value
    .split(/[,，;\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function PipelineGeneratorPanel({ onCompleted }: PipelineGeneratorPanelProps) {
  const [knowledgePoints, setKnowledgePoints] = useState<KnowledgePoint[]>([]);
  const [providers, setProviders] = useState<string[]>(["mock"]);
  const [stage, setStage] = useState("初中");
  const [dimensions, setDimensions] = useState<string[]>([]);
  const [secondaryDimensions, setSecondaryDimensions] = useState<string[]>([]);
  const [knowledgeCodesText, setKnowledgeCodesText] = useState("");
  const [countPerKnowledgePoint, setCountPerKnowledgePoint] = useState(1);
  const [limitPerDimension, setLimitPerDimension] = useState(1);
  const [maxKnowledgePoints, setMaxKnowledgePoints] = useState(0);
  const [promptBatchSize, setPromptBatchSize] = useState(5);
  const [difficultyTarget, setDifficultyTarget] = useState("medium");
  const [cognitiveLevelTarget, setCognitiveLevelTarget] = useState("");
  const [similarityThreshold, setSimilarityThreshold] = useState(0.82);
  const [writeDrafts, setWriteDrafts] = useState(true);
  const [requirement, setRequirement] = useState("生成初中 AI 素养场景化单选题，选项要有区分度。");
  const [running, setRunning] = useState(false);
  const [loadingPoints, setLoadingPoints] = useState(true);
  const [error, setError] = useState("");
  const [result, setResult] = useState<PipelineResult | null>(null);

  useEffect(() => {
    async function loadKnowledgePoints() {
      setLoadingPoints(true);
      try {
        const response = await fetch("/api/knowledge-points", { cache: "no-store" });
        if (!response.ok) {
          throw new Error("知识点加载失败");
        }
        setKnowledgePoints((await response.json()) as KnowledgePoint[]);
      } catch (currentError) {
        setError(currentError instanceof Error ? currentError.message : "知识点加载失败");
      } finally {
        setLoadingPoints(false);
      }
    }

    void loadKnowledgePoints();
  }, []);

  const availableSecondaryDimensions = useMemo<string[]>(
    () => dimensions.flatMap((dimension) => [...getSecondaryDimensions(dimension)]),
    [dimensions]
  );

  const matchingKnowledgePoints = useMemo(() => {
    const wantedCodes = splitCodes(knowledgeCodesText);
    const wantedCodeSet = new Set(wantedCodes);
    return knowledgePoints.filter((point) => {
      if (stage && point.stage !== stage) {
        return false;
      }
      if (wantedCodeSet.size > 0) {
        return wantedCodeSet.has(point.knowledgeCode);
      }
      if (dimensions.length > 0 && !dimensions.includes(point.primaryDimension)) {
        return false;
      }
      if (secondaryDimensions.length > 0 && !secondaryDimensions.includes(point.secondaryDimension)) {
        return false;
      }
      return true;
    });
  }, [dimensions, knowledgeCodesText, knowledgePoints, secondaryDimensions, stage]);

  useEffect(() => {
    setSecondaryDimensions((current) => current.filter((item) => availableSecondaryDimensions.includes(item)));
  }, [availableSecondaryDimensions]);

  const plannedKnowledgePoints =
    splitCodes(knowledgeCodesText).length > 0
      ? matchingKnowledgePoints.length
      : dimensions.length > 0
        ? Math.min(
            matchingKnowledgePoints.length,
            maxKnowledgePoints > 0 ? maxKnowledgePoints : dimensions.length * limitPerDimension
          )
        : Math.min(
            matchingKnowledgePoints.length,
            maxKnowledgePoints > 0 ? maxKnowledgePoints : aiLiteracyDimensions.length * limitPerDimension
          );
  const plannedCandidates = plannedKnowledgePoints * providers.length * countPerKnowledgePoint;

  async function runPipeline(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (providers.length === 0) {
      setError("请至少选择一个模型 provider。");
      return;
    }

    setRunning(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("/api/question-pipeline/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "frontend-pipeline-run",
          stage,
          providers,
          dimensions,
          secondaryDimensions,
          knowledgeCodes: splitCodes(knowledgeCodesText),
          questionType: "单选",
          countPerKnowledgePoint,
          limitPerDimension,
          maxKnowledgePoints,
          promptBatchSize,
          difficultyTarget,
          cognitiveLevelTarget,
          requirement,
          similarityThreshold,
          writeDrafts,
          outputDir: "outputs/question-pipeline"
        })
      });
      const payload = (await response.json()) as PipelineResult | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload ? payload.error : "流水线运行失败");
      }

      setResult(payload as PipelineResult);
      await onCompleted();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "流水线运行失败");
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="panel pipeline-panel">
      <div className="panel-header">
        <div>
          <h2>流水线出题演示</h2>
          <span className="muted">
            {loadingPoints ? "知识点加载中..." : `当前匹配 ${matchingKnowledgePoints.length} 个知识点`}
          </span>
        </div>
        <span className="badge">预计 {plannedCandidates} 道候选题</span>
      </div>

      {error ? <div className="error-box pipeline-message">{error}</div> : null}

      <form className="form-body" onSubmit={runPipeline}>
        <div className="form-grid">
          <label className="form-row">
            <span>学段</span>
            <input value={stage} onChange={(event) => setStage(event.target.value)} />
          </label>
          <label className="form-row">
            <span>每知识点题数</span>
            <input
              min={1}
              max={20}
              type="number"
              value={countPerKnowledgePoint}
              onChange={(event) => setCountPerKnowledgePoint(Math.max(1, Number(event.target.value) || 1))}
            />
          </label>
          <label className="form-row">
            <span>每维度知识点上限</span>
            <input
              min={0}
              type="number"
              value={limitPerDimension}
              onChange={(event) => setLimitPerDimension(Math.max(0, Number(event.target.value) || 0))}
            />
          </label>
          <label className="form-row">
            <span>总知识点上限（0 不限制）</span>
            <input
              min={0}
              type="number"
              value={maxKnowledgePoints}
              onChange={(event) => setMaxKnowledgePoints(Math.max(0, Number(event.target.value) || 0))}
            />
          </label>
          <label className="form-row">
            <span>Prompt 批大小</span>
            <input
              min={1}
              max={20}
              type="number"
              value={promptBatchSize}
              onChange={(event) => setPromptBatchSize(Math.max(1, Number(event.target.value) || 1))}
            />
          </label>
          <label className="form-row">
            <span>相似度阈值</span>
            <input
              max={1}
              min={0}
              step={0.01}
              type="number"
              value={similarityThreshold}
              onChange={(event) => setSimilarityThreshold(Math.max(0, Math.min(1, Number(event.target.value) || 0)))}
            />
          </label>
          <label className="form-row">
            <span>目标难度</span>
            <select value={difficultyTarget} onChange={(event) => setDifficultyTarget(event.target.value)}>
              {difficultyOptions.map((difficulty) => (
                <option key={difficulty} value={difficulty}>
                  {difficulty}
                </option>
              ))}
            </select>
          </label>
          <label className="form-row">
            <span>认知层级</span>
            <select value={cognitiveLevelTarget} onChange={(event) => setCognitiveLevelTarget(event.target.value)}>
              {cognitiveOptions.map((level) => (
                <option key={level || "auto"} value={level}>
                  {level || "auto"}
                </option>
              ))}
            </select>
          </label>
          <label className="form-row full">
            <span>Provider</span>
            <div className="choice-grid">
              {providerOptions.map((provider) => (
                <label className="filter-choice" key={provider}>
                  <input
                    checked={providers.includes(provider)}
                    type="checkbox"
                    onChange={() => setProviders((current) => toggleValue(current, provider))}
                  />
                  <span>{provider}</span>
                </label>
              ))}
            </div>
          </label>
          <label className="form-row full">
            <span>一级维度</span>
            <div className="choice-grid">
              {aiLiteracyDimensions.map((dimension) => (
                <label className="filter-choice" key={dimension}>
                  <input
                    checked={dimensions.includes(dimension)}
                    type="checkbox"
                    onChange={() => setDimensions((current) => toggleValue(current, dimension))}
                  />
                  <span>{dimension}</span>
                </label>
              ))}
            </div>
          </label>
          <label className="form-row full">
            <span>二级维度</span>
            {dimensions.length === 0 ? (
              <p className="muted">未选择一级维度时，默认每个一级维度取若干知识点。</p>
            ) : (
              <div className="choice-grid secondary-choice-grid">
                {availableSecondaryDimensions.map((dimension) => (
                  <label className="filter-choice" key={dimension}>
                    <input
                      checked={secondaryDimensions.includes(dimension)}
                      type="checkbox"
                      onChange={() => setSecondaryDimensions((current) => toggleValue(current, dimension))}
                    />
                    <span>{dimension}</span>
                  </label>
                ))}
              </div>
            )}
          </label>
          <label className="form-row full">
            <span>指定知识点编码（可选，逗号/换行分隔）</span>
            <textarea
              value={knowledgeCodesText}
              onChange={(event) => setKnowledgeCodesText(event.target.value)}
              placeholder="例如：J-U-1.1.1.1-0001"
            />
          </label>
          <label className="form-row full">
            <span>出题要求</span>
            <textarea value={requirement} onChange={(event) => setRequirement(event.target.value)} />
          </label>
          <label className="inline-check">
            <input checked={writeDrafts} type="checkbox" onChange={(event) => setWriteDrafts(event.target.checked)} />
            <span>通过校验后写入 question_drafts</span>
          </label>
        </div>

        <div className="toolbar" style={{ marginTop: 14 }}>
          <button className="primary" disabled={running || plannedKnowledgePoints === 0} type="submit">
            {running ? "流水线运行中..." : "开始生成"}
          </button>
          <span className="muted">
            将处理 {plannedKnowledgePoints} 个知识点，生成约 {plannedCandidates} 道候选题
          </span>
        </div>
      </form>

      {result ? (
        <div className="pipeline-result">
          <div className="pipeline-stats">
            <span className="badge">知识点 {result.selectedKnowledgePoints}</span>
            <span className="badge">候选题 {result.generatedCandidates}</span>
            <span className="badge status-reviewed">写入草稿 {result.createdDrafts}</span>
            <span className={result.errors.length ? "badge job-status-failed" : "badge job-status-completed"}>
              错误 {result.errors.length}
            </span>
          </div>
          <p className="muted">
            报告：{result.reportJson}；{result.reportCsv}
          </p>
          {result.errors.length > 0 ? (
            <div className="error-box">
              {result.errors.map((item) => (
                <div key={item}>{item}</div>
              ))}
            </div>
          ) : null}
          <div className="pipeline-candidates">
            {result.candidates.slice(0, 5).map((candidate) => (
              <article className="pipeline-candidate" key={`${candidate.provider}-${candidate.index}`}>
                <div className="badge-row">
                  <span className="badge">{candidate.provider}</span>
                  <span className={candidate.passed ? "badge status-reviewed" : "badge job-status-failed"}>
                    {candidate.passed ? "通过" : "拦截"}
                  </span>
                  <span className="badge">结构 {candidate.structureResult}</span>
                  <span className="badge">质量 {candidate.qualityLevel}</span>
                  <span className="badge">相似度 {Number(candidate.duplicateScore || 0).toFixed(2)}</span>
                </div>
                <strong>{candidate.title}</strong>
                <p>{candidate.scenario}</p>
                <p>{candidate.question}</p>
                <p className="muted">
                  {candidate.knowledgeCode} · {candidate.primaryDimension} · {candidate.secondaryDimension} ·{" "}
                  {candidate.knowledgePoint}
                </p>
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
