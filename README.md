# AI素养测评题库系统

一个本地运行的题库管理 MVP，用于维护 AI 素养测评的结构化题目。当前只做题库管理，不包含登录、考试、答题记录、权限和云数据库。

## 技术栈

- Next.js + TypeScript
- 本地 JSON 文件存储
- 数据文件：`data/questions.json`
- 样例题库：`data/sample_questions.json`

## 安装与运行

```bash
npm install
npm run dev
```

打开浏览器访问：

```text
http://localhost:3000
```

生产构建：

```bash
npm run build
npm run start
```

代码检查：

```bash
npm run lint
```

## 功能

- 题目列表
- 新增题目
- 编辑题目
- 删除题目
- 查看题目详情
- 按一级维度、状态、难度、标签筛选
- 搜索标题、题干和场景
- 导出全部题库为 JSON
- 从 JSON 批量导入题目

## 题目字段

每道题包含：

- `id`
- `title`
- `question`
- `scenario`
- `options`
- `correctAnswer`
- `explanation`
- `dimension`
- `subSkill`
- `cognitiveLevel`
- `difficultyEstimate`
- `tags`
- `sourceReference`
- `status`
- `createdAt`
- `updatedAt`

TypeScript 类型定义在 `types/question.ts`。

## 导入题库

1. 进入首页。
2. 点击“导入 JSON”。
3. 选择符合结构的 JSON 文件，例如 `data/sample_questions.json`。
4. 系统会按 `id` 合并导入：相同 `id` 会覆盖，新的 `id` 会新增。

导入文件必须是题目数组：

```json
[
  {
    "id": "sample-001",
    "title": "题目标题",
    "question": "题干",
    "scenario": "场景描述",
    "options": [
      { "id": "A", "text": "选项 A" },
      { "id": "B", "text": "选项 B" }
    ],
    "correctAnswer": "A",
    "explanation": "解析",
    "dimension": "AI信息判断",
    "subSkill": "结果核验",
    "cognitiveLevel": "apply",
    "difficultyEstimate": "easy",
    "tags": ["AI", "场景题"],
    "sourceReference": "自编场景题",
    "status": "draft",
    "createdAt": "2026-05-27T00:00:00.000Z",
    "updatedAt": "2026-05-27T00:00:00.000Z"
  }
]
```

## 导出题库

点击首页“导出 JSON”，系统会下载当前 `data/questions.json` 中的全部题目。

## 数据存储说明

当前版本使用本地 JSON 文件，便于查看、备份、迁移和版本管理。后续如果要支持正式考试、题目统计、自适应测评或多人协作，可以把 `lib/questions.ts` 替换为 SQLite 或云数据库实现，页面和类型结构可以继续复用。

## LLM provider

Draft generation can use `mock`, `openai`, or `deepseek`.

For OpenAI/GPT credits, set these values in `.env.local`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.5
OPENAI_BASE_URL=https://api.openai.com/v1
```

The app calls the OpenAI Responses API and asks the model to return structured JSON drafts. Drafts still receive no `itemCode`; `itemCode` is assigned only after a draft is accepted into the formal question bank.

### Provider notes while framework is being finalized

Current local default is `LLM_PROVIDER=mock`, so draft generation does not spend API quota.

GPT/OpenAI settings are kept as standby comments in `.env.local` and `.env.example`; uncomment them later when switching back to GPT.

For the Xunfei MaaS/OpenAI-compatible service, the project currently has placeholder env keys:

```env
LLM_PROVIDER=xfyun
XFYUN_MAAS_API_KEY=
XFYUN_MAAS_MODEL=Qwen3.6-35B-A3B
XFYUN_MAAS_BASE_URL=https://maas-api.cn-huabei-1.xf-yun.com/v2
```

Before wiring it fully, confirm the HTTP endpoint path, auth header format, whether `/chat/completions` is supported, and whether JSON output or `response_format` is supported.
