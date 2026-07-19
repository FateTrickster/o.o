# Textbook RAG Vector Database

The vector database is not tracked in Git due to its size (~51 MB).
Download it from the [GitHub Releases](https://github.com/QS0186/o.o/releases) page
and place it in this directory.

## File

- **Name**: `zhishitupu.db`
- **Size**: ~51 MB
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

## Default Path

The application expects the database at `backend/data/rag/zhishitupu.db`.
Override with the `RAG_DATABASE_PATH` environment variable.
