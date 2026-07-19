# Textbook RAG Vector Database

The vector database is not tracked in Git due to its size (~51 MB).
Download it from the GitHub Release and place it in this directory.

## Quick Setup (PowerShell)

```powershell
# Download
Invoke-WebRequest -Uri "https://github.com/FateTrickster/o.o/releases/download/rag-db-v1/zhishitupu.db" -OutFile "backend/data/rag/zhishitupu.db"

# Verify SHA256
(Get-FileHash -Path "backend/data/rag/zhishitupu.db" -Algorithm SHA256).Hash.ToLower()
# Expected: 93b353a68d68171f451e663ba070ebbd1449285a21346dfe54613c21809218af
```

## Download

- **Release**: [Textbook RAG Vector Database v1](https://github.com/FateTrickster/o.o/releases/tag/rag-db-v1)
- **Direct download**: `https://github.com/FateTrickster/o.o/releases/download/rag-db-v1/zhishitupu.db`

## File

- **Name**: `zhishitupu.db`
- **Target path**: `backend/data/rag/zhishitupu.db`
- **Size**: 53489664 bytes (~51 MB)
- **SHA256**: `93b353a68d68171f451e663ba070ebbd1449285a21346dfe54613c21809218af`

## Contents

| Table | Rows | Description |
|-------|------|-------------|
| `document` | 2090 | Source textbook documents |
| `chunk` | 2090 | Text chunks with metadata |
| `chunk_embedding` | 2090 | `text-embedding-v4` vectors (1024-dim, FLOAT) |

## Embedding Model

- Provider: DashScope (Alibaba Cloud)
- Model: `text-embedding-v4`
- Dimensions: 1024
- Endpoint: OpenAI-compatible (`https://dashscope.aliyuncs.com/compatible-mode/v1`)

## Configuration

After placing the database, configure `DASHSCOPE_API_KEY` in `.env.local`:

```env
DASHSCOPE_API_KEY=<your-key>
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_EMBEDDING_DIMENSIONS=1024
```

Never commit `.env.local`. See `.env.example` for all supported variables.

## Default Path

The application expects the database at `backend/data/rag/zhishitupu.db`.
Override with the `RAG_DATABASE_PATH` environment variable.
