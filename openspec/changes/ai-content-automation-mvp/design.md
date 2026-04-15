## Context

头脑风暴设计文档（`docs/superpowers/specs/2026-04-14-ai-content-automation-mvp-design.md`）已确认 MVP 路径与里程碑：M1（抓取 + 归一 + 规则 + 队列）→ M2（生成 + 审核 + 发布包）→ M3（可观测性）。技术基线：Python 3.11 / FastAPI、React 18 / TypeScript / Vite、PostgreSQL 15（SQLAlchemy + Alembic）、RabbitMQ + Celery、Redis、Docker Compose + bind mount（见 `openspec/config.yaml`）。

## Goals / Non-Goals

**Goals:**

- 主链路可观测、可重试、状态机全程可审计
- 抓取器插件化隔离，单源故障不阻全链路
- 所有长耗时任务在 Celery worker 执行，API 层不阻塞
- 数据库结构仅通过 Alembic migration 演进
- 配置经环境变量注入，无硬编码敏感信息
- M1→M2→M3 每个里程碑有独立可验收产出

**Non-Goals:**

- 抖音/小红书自动发布 API（MVP 后）
- 短视频 TTS + 混剪（MVP 后）
- 多租户、复杂权限与计费（MVP 后）

## Decisions

| 决策点 | 选择 | 备选 | 理由 |
|--------|------|------|------|
| 异步执行 | Celery + RabbitMQ（rules 规定） | FastAPI BackgroundTasks | 支持重试、隔离、水平扩展；单队列故障可独立恢复 |
| 抓取扩展 | 每平台独立 collector 插件 + 统一 `topic_raw` schema | 每源独立微服务 | MVP 复杂度可控，插件边界已隔离单源故障 |
| 去重策略首版 | 规范化标题 + 关键词 + 时间窗指纹 | 重度语义向量相似度 | 降低首版依赖，接口保留演进；语义去重可迭代升级 |
| 双平台稿 | 共用中间稿 + 平台适配层（两条 `content_asset` 行） | 每平台独立两次 DeepSeek 调用 | 成本/质量/一致性平衡；中间稿可复用审核 |
| 发布包格式 | 版本化结构化 JSON/zip（DB 记录 + 本地文件/路径），带版本号防覆盖 | 直接写对象存储 | MVP 可追溯优先；对象存储可后续接入 |
| 运行时 | Docker Compose 固定服务名 + 开发 bind mount | 纯宿主机进程 | 与仓库规则一致，环境标准化，onboarding 快 |

## Risks / Trade-offs

- **[Risk] 反爬与选择器失效** → 按源退避重试 + 插件边界隔离；健康检查可暴露来源状态；抓取策略可替换。
- **[Risk] DeepSeek 限流 / 内容安全** → 错误分类（超时/限流/内容安全/模板异常）+ 重试上限 + 支持手动重入队；规则引擎前置敏感词过滤。
- **[Risk] 一稿多投质量参差** → 平台模板分层 + 审核样本集回归追踪一次通过率趋势。
- **[Trade-off] 语义去重首版简化** → 短期可能存在少量重复话题，通过 TopN 与主题配额运营侧缓解。
- **[Trade-off] 发布包先用本地文件** → 后期接对象存储时需迁移 `publish_package.download_url` 字段；接口设计需预留 URL 字段。

## Migration Plan

- 无存量数据迁移；Alembic 从空库演进，首次迁移覆盖 M1 全部实体。
- 本地启动顺序：`docker compose up -d postgres rabbitmq redis` → `alembic upgrade head` → `docker compose up backend worker frontend`。
- 回滚：`alembic downgrade -1`（或指定版本）+ 上一镜像；任务队列幂等，重跑安全。

## Open Questions

- DeepSeek 具体模型名、最大 token、超时与重试上限最终值——在实现前写入 `.env.example` 与配置表，由实现者确认。
- 发布包对外交付形式（本地下载 vs 预签名 URL）——M2 收尾前与运营确认后更新 `publish_package` schema。
