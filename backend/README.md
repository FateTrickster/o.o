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

## Notes

This MVP intentionally uses the Python standard `sqlite3` module to keep the first migration small. A later phase can replace repositories with SQLAlchemy and Alembic migrations.
