# Python Backend MVP

This backend is the first Python step for the AI literacy question pipeline.

It is now the runtime data source for the Next.js UI. The Next `/api/*` routes proxy to this FastAPI service for persisted question, knowledge, and draft data.

- initialize a local SQLite database
- seed the UACE framework
- import existing `data/knowledge.json`, `data/drafts.json`, and `data/questions.json`
- call Xfyun MaaS to generate question drafts
- track each draft generation run in `generation_jobs`
- split large generation requests into smaller `generation_batches`
- store generated drafts in SQLite
- list, view, create, edit, and delete knowledge entries
- list, edit, delete, and accept generated drafts
- list, view, create, import, edit, and delete formal questions
- accept a draft into the formal question table with an auto-incrementing `itemCode`

## Install

```bash
cd backend
python -m pip install -r requirements.txt
```

## Run

From the project root:

```bash
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Initialize Data

```bash
curl -X POST http://127.0.0.1:8000/admin/init-db
curl -X POST http://127.0.0.1:8000/admin/import-json ^
  -H "Content-Type: application/json" ^
  -d "{\"reset\": false}"
```

The service reads Xfyun settings from the project `.env.local`:

```env
XFYUN_MAAS_API_KEY=
XFYUN_MAAS_MODEL=xopqwen36v35b
XFYUN_MAAS_BASE_URL=https://maas-api.cn-huabei-1.xf-yun.com/v2
```

## Generate Drafts

```json
POST /drafts/generate
{
  "knowledgeIds": ["knowledge-entry-id"],
  "requirement": "生成 3 道场景化单选题",
  "targetDimensions": ["应用AI（Apply）"],
  "targetSecondaryDimensions": ["能对AI生成结果的准确性和合理性进行判断"],
  "targetTags": ["事实核查"],
  "count": 3
}
```

## Generate Drafts From IDE Terminal

Run a dry run first. This only prints the plan and does not call the API:

```bash
python -m backend.app.scripts.generate_drafts --per-knowledge 3 --max-knowledge 5 --dry-run
```

Generate drafts after the plan looks right:

```bash
python -m backend.app.scripts.generate_drafts --per-knowledge 3 --max-knowledge 5
```

Generate drafts with DeepSeek for comparison:

```bash
python -m backend.app.scripts.generate_drafts ^
  --provider deepseek ^
  --per-knowledge 2 ^
  --max-knowledge 3 ^
  --requirement "Generate junior-high AI literacy scenario-based single-choice questions."
```

Useful options:

```bash
python -m backend.app.scripts.generate_drafts ^
  --per-knowledge 3 ^
  --max-knowledge 20 ^
  --dimension "理解AI（Understand）" ^
  --secondary-dimension "知道人工智能的基本概念（如机器学习、生成式AI等）" ^
  --tag "机器学习" ^
  --requirement "生成初中 AI 素养场景化单选题，选项要有区分度。" ^
  --pause-seconds 2
```

Notes:

- `--per-knowledge` is limited to 1-20 because one backend request is capped at 20.
- `--tag` can be repeated or comma-separated. It filters knowledge entries and is also passed into the generation prompt as target tags.
- Generated questions are saved as drafts in `question_drafts`; they are not formal questions until accepted.
- Open `backend/data/ai_literacy.db` in Navicat and refresh/reconnect to inspect the SQLite tables.

## Import Completed Workbook Questions

Import completed questions from `knowledge/AI素养题库设计.xlsx` into the formal `questions` table:

```bash
python -m backend.app.scripts.import_knowledge_points --dry-run
python -m backend.app.scripts.import_knowledge_points
python -m backend.app.scripts.import_workbook_questions --dry-run
python -m backend.app.scripts.import_workbook_questions
python -m backend.app.scripts.backfill_question_metadata
```

`import_knowledge_points` builds the normalized `knowledge_points` table from the workbook's knowledge sheets. The question importer reads the `理解AI`, `使用AI`, `创造AI`, and `AI伦理` sheets, assigns normal `itemCode` values, and uses stable IDs so rerunning the command updates the same imported questions instead of duplicating them. `backfill_question_metadata` fills the newer normalized columns on existing formal questions where possible.

## Codex-Assisted Draft Generation

Use this when Codex is helping generate higher-quality drafts in the current repo instead of calling an external LLM API directly.

Step 1: export a knowledge-backed generation plan:

```bash
python -m backend.app.scripts.codex_draft_tool plan ^
  --per-knowledge 2 ^
  --max-knowledge 3 ^
  --output data/codex_generation_plan.json
```

Give the generated `data/codex_generation_plan.json` to Codex in the current thread. Codex should return JSON matching the plan's `outputSchema`.

Step 2: validate the generated JSON without writing to SQLite:

```bash
python -m backend.app.scripts.codex_draft_tool import ^
  --input data/codex_generated_drafts.json ^
  --dry-run
```

Step 3: import valid drafts into SQLite:

```bash
python -m backend.app.scripts.codex_draft_tool import ^
  --input data/codex_generated_drafts.json ^
  --requirement "Codex assisted draft generation from knowledge chunks"
```

This writes drafts into `question_drafts` and creates audit records in `generation_jobs` / `generation_batches` with `provider=codex`.

## Small Provider Comparison

A lightweight comparison can use the same knowledge scope and count:

```bash
python -m backend.app.scripts.generate_drafts --provider xfyun --per-knowledge 2 --max-knowledge 3
python -m backend.app.scripts.generate_drafts --provider deepseek --per-knowledge 2 --max-knowledge 3
python -m backend.app.scripts.codex_draft_tool plan --per-knowledge 2 --max-knowledge 3 --output data/codex_generation_plan.json
```

Use the generated plan for Codex-assisted questions, then import them with `codex_draft_tool import`. Compare the resulting drafts by `generation_jobs.provider`.

## Knowledge-Point Question Pipeline

Use this newer pipeline when you want the backend to run the full right-side generation flow from the normalized `knowledge_points` table:

```bash
python -m backend.app.scripts.generate_question_pipeline --provider mock --limit-per-dimension 1 --dry-run
```

Generate candidates and write only passed, non-duplicate items into `question_drafts`:

```bash
python -m backend.app.scripts.generate_question_pipeline ^
  --provider xfyun ^
  --limit-per-dimension 5 ^
  --count-per-knowledge-point 2 ^
  --prompt-batch-size 5 ^
  --requirement "生成初中 AI 素养场景化单选题，选项要有区分度。" ^
  --write-drafts ^
  --output-dir outputs/question-pipeline
```

Run multiple providers for comparison:

```bash
python -m backend.app.scripts.generate_question_pipeline ^
  --provider xfyun ^
  --provider deepseek ^
  --limit-per-dimension 3 ^
  --count-per-knowledge-point 1 ^
  --write-drafts
```

Useful filters:

```bash
python -m backend.app.scripts.generate_question_pipeline ^
  --dimension "理解AI（Understand）" ^
  --secondary-dimension "概念认知" ^
  --knowledge-code J-U-1.1.1.1-0001 ^
  --show-prompt ^
  --dry-run
```

The pipeline does this in order:

- reads task config from CLI or `--config task.json`
- selects knowledge points by stage, dimension, secondary dimension, or knowledge code
- builds a reusable structured JSON prompt
- calls one or more providers (`mock`, `xfyun`, `deepseek`)
- normalizes options/answers/tags
- checks structure, quality, and duplicate similarity
- writes passed candidates into `question_drafts` only when `--write-drafts` is set
- outputs JSON and CSV reports under `outputs/`

## Core Endpoints

```text
GET    /health
POST   /admin/init-db
POST   /admin/import-json
GET    /framework
GET    /knowledge
POST   /knowledge
POST   /knowledge/import
GET    /knowledge/{entry_id}
PUT    /knowledge/{entry_id}
DELETE /knowledge/{entry_id}
GET    /drafts
GET    /generation-jobs
GET    /generation-batches
GET    /drafts/{draft_id}
PUT    /drafts/{draft_id}
DELETE /drafts/{draft_id}
POST   /drafts/{draft_id}/accept
GET    /questions
POST   /questions
POST   /questions/import
GET    /questions/{question_id}
PUT    /questions/{question_id}
DELETE /questions/{question_id}
```

## Textbook RAG (Optional)

The question pipeline can retrieve textbook chunks as generation evidence.

- RAG is disabled by default (`useRag=false` in `POST /question-pipeline/run`, `use_rag=false` in task config JSON).
- Enable it by setting `useRag=true` and optionally `ragTopK` (1-5, default 3).
- Requires Python 3.12 and the `duckdb` / `numpy` / `openai` dependencies from `requirements.txt`.
- Requires `DASHSCOPE_API_KEY` in the environment or `.env.local` (see `.env.example`). Never commit `.env.local`.
- Embedding model: `text-embedding-v4` (DashScope OpenAI-compatible endpoint, 1024-dim vectors).
- The vector database is at `backend/data/rag/zhishitupu.db` (~51 MB, 2090 chunks × 1024-dim). It is tracked via Git LFS. Override with `RAG_DATABASE_PATH` if needed.
- When RAG is enabled and the database or API key is missing, the pipeline fails with an explicit error instead of silently generating without textbook evidence.

### Run Tests

```bash
py -3.12 -m unittest discover -s backend/tests -p "test_*.py" -v
```

## Notes

This MVP intentionally uses the Python standard `sqlite3` module to keep the first migration small. A later phase can replace repositories with SQLAlchemy and Alembic migrations.
