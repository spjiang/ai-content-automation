## 1. 仓库基线与运行环境

- [x] 1.1 初始化后端 FastAPI 工程目录结构（api/application/domain/infrastructure 分层、健康检查接口）
- [x] 1.2 初始化前端 React 18 + Vite + TypeScript 工程（pages/features/shared 骨架）
- [x] 1.3 编写 `docker-compose.yml`：backend、frontend、postgres、rabbitmq、redis、worker，开发态 bind mount 与 healthcheck
- [x] 1.4 提供 `.env.example`（含 DeepSeek key 占位、DB/MQ 连接串、超时与重试配置）与 README 启动说明

## 2. M1：数据入口（抓取 → 归一 → 规则 → 队列）

- [x] 2.1 Alembic 初始化：首版 migration 创建 `topic_raw`、`topic_canonical` 实体及必要索引
- [x] 2.2 定义 collector 插件接口（抽象基类/协议），实现三源占位 collector（结构完整，数据可 mock）
- [x] 2.3 实现 normalizer：字段清洗、指纹去重（规范化标题+关键词+时间窗）、热度归一与权重排序、TopN 配额输出
- [x] 2.4 实现 rule-engine：规则配置加载、黑白名单/关键词/敏感词/热度阈值过滤、命中明细持久化（含规则版本标识）
- [x] 2.5 Celery 任务入队：`content_job` 创建（状态 `QUEUED`）、按源退避重试、失败计数与告警钩子触发

## 3. M2：生成 → 审核 → 发布包（业务闭环）

- [ ] 3.1 Alembic migration：新增 `content_job`、`content_asset`（双平台版本行）、状态字段与状态机约束
- [ ] 3.2 DeepSeek 客户端：HTTP 封装、超时/限流/内容安全错误分类、重试策略；读取 env 配置
- [ ] 3.3 Worker 消费生成队列：执行 DeepSeek 调用、写入双平台 `content_asset`、状态迁移 `GENERATING`→`GENERATED`；幂等保障
- [ ] 3.4 记录生成版本元数据：规则版本、提示词版本、平台模板版本写入 `content_job`，不可被后续操作覆盖
- [ ] 3.5 Alembic migration：新增 `review_record`、`publish_package`（版本号、生成时间、有效期、可空效果字段、`download_url` 占位）
- [ ] 3.6 审核 API：`POST /api/v1/review`（通过/驳回），状态迁移 `IN_REVIEW`→`APPROVED` 或 `REVISE_REQUIRED`；写入 `review_record`；支持修订后重新入队（新版本资产，不覆盖旧版）
- [ ] 3.7 发布包生成：`APPROVED` 后打包为版本化结构化产出物，带唯一版本号防覆盖；打包失败可重试
- [ ] 3.8 发布包导出/下载 API：`GET /api/v1/packages/{id}/download`（MVP 返回文件或本地路径，预留 `download_url` 字段）
- [ ] 3.9 前端审核台：内容列表（状态筛选）、详情页（双平台稿件预览）、通过/驳回操作、发布包下载入口

## 4. M3：可运营性（监控、指标、工具）

- [ ] 4.1 全链路结构化日志埋点：抓取、归一、规则、生成、审核、打包各阶段关键事件与耗时
- [ ] 4.2 基础告警钩子：连续抓取失败、队列积压超阈值、生成失败率告警；健康聚合接口 `GET /api/v1/health`
- [ ] 4.3 指标查询接口或导出：审核通过率（含一次通过率）、抓取/生成成功率、链路 P50/P90 最小可用集
- [ ] 4.4 规则命中回放：只读查询 API，输入话题 id 可返回规则命中明细，支撑误杀/漏放排查

## 5. 测试与质量门禁

- [ ] 5.1 后端单测：状态机关键迁移（含 `FAILED`/`REVISE_REQUIRED`）、规则命中逻辑、幂等行为（pytest + pytest-asyncio）
- [ ] 5.2 后端集成测试：抓取→归一→入队、生成→写资产链路（testcontainers 或 CI 约定的 DB/MQ 服务）
- [ ] 5.3 前端测试：审核台核心交互（列表加载、通过/驳回操作、状态更新）（Vitest + React Testing Library）
- [ ] 5.4 Lint/Type 检查脚本：后端 ruff + black + isort + mypy；前端 eslint + prettier + vitest；与 CI 流程对齐
