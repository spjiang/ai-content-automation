## Why

内容创作团队在发现热点、生成图文、多平台分发上依赖大量人工操作，效率低且难以规模化。本变更构建从热点抓取到双平台图文产出的 MVP 自动化闭环，先以人工发布验证业务价值，再逐步扩展自动发布能力。

## What Changes

- **新增**：三源热点抓取（微博热搜、知乎热榜、抖音热榜），插件化架构便于扩展
- **新增**：热点归一化、去重排序（指纹 + 时间窗 + 权重）与规则引擎（黑白名单、关键词、敏感词、热度阈值）
- **新增**：Celery + RabbitMQ 异步生成任务，调用 DeepSeek 产出抖音/小红书双平台图文稿件（一稿多投）
- **新增**：人工审核流（通过/驳回/修订）、版本链与结构化发布包导出
- **新增**：核心实体与状态机（`NEW`→`QUEUED`→`GENERATING`→`GENERATED`→`IN_REVIEW`→`APPROVED`→`PACKAGED`，含 `FAILED`/`REVISE_REQUIRED`）
- **MVP 明确不含**：平台自动发布 API、短视频生成（TTS+混剪）、多租户/复杂计费

## Capabilities

### New Capabilities

- `topic-ingestion-pipeline`：插件化三源抓取、归一去重与排序、规则引擎过滤与入队；单源故障不阻全链路
- `ai-dual-platform-generation`：DeepSeek 双平台稿件生成、失败分类与重试、提示词与模板版本化
- `review-and-publish-package`：人工审核与版本链、发布包版本化导出、业务效果回填字段预留

### Modified Capabilities

- （无）当前 `openspec/specs/` 下无既有能力规格，本次均为新增

## Impact

- **后端**：FastAPI `/api/v1` 路由、SQLAlchemy 模型（6 个核心实体）、Alembic migration、Celery worker 与 RabbitMQ broker、抓取器插件接口
- **前端**：最小审核控制台与发布包下载入口（React/TypeScript），仅通过后端 API 访问
- **数据**：PostgreSQL 中全量新建实体与索引，无存量迁移
- **基础设施**：Docker Compose（backend/frontend/postgres/rabbitmq/redis/worker）、开发态 bind mount、健康检查；端口约定见 `openspec/config.yaml`
- **合规与运维**：规则命中审计、内容安全前置、全链路埋点（M3 深化为告警看板）
