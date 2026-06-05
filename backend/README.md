# Python Backend MVP

This backend is the first Python step for the AI literacy question pipeline.

It does not replace the Next.js UI yet. It provides a standalone FastAPI service that can:

- initialize a local SQLite database
- seed the UACE framework
- import existing `data/knowledge.json`, `data/drafts.json`, and `data/questions.json`
- call Xfyun MaaS to generate question drafts
- store generated drafts in SQLite
- list, edit, delete, and accept generated drafts
- list, view, and delete formal questions
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

## Core Endpoints

```text
GET    /health
POST   /admin/init-db
POST   /admin/import-json
GET    /framework
GET    /knowledge
GET    /drafts
GET    /drafts/{draft_id}
PUT    /drafts/{draft_id}
DELETE /drafts/{draft_id}
POST   /drafts/{draft_id}/accept
GET    /questions
GET    /questions/{question_id}
DELETE /questions/{question_id}
```

## Notes

This MVP intentionally uses the Python standard `sqlite3` module to keep the first migration small. A later phase can replace repositories with SQLAlchemy and Alembic migrations.
