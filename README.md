# AI Content Automation

自动化内容生成与发布系统 MVP —— 热点抓取 → DeepSeek 图文生成 → 人工审核 → 发布包导出。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11 / FastAPI 0.115 / SQLAlchemy 2 / Alembic |
| 异步任务 | Celery 5 + RabbitMQ 3.12 |
| 缓存 | Redis 7 |
| 数据库 | PostgreSQL 15 |
| 前端 | React 18 / TypeScript / Vite / pnpm |
| 容器 | Docker Compose（开发态 bind mount） |

## 端口约定

| 服务 | 端口 |
|---|---|
| backend API | 8000 |
| frontend dev | 5173 |
| postgres | 5432 |
| rabbitmq amqp | 5672 |
| rabbitmq management | 15672 |
| redis | 6379 |

## 快速启动

### 1. 准备环境变量

```bash
cp .env.example .env
# 修改 .env 中的密码与 DEEPSEEK_API_KEY
```

### 2. 启动基础设施

```bash
docker compose up -d postgres rabbitmq redis
```

### 3. 执行数据库迁移

```bash
docker compose run --rm backend alembic upgrade head
```

### 4. 启动全部服务

```bash
docker compose up -d
```

### 5. 验证

- API 文档：http://localhost:8000/api/v1/docs
- 健康检查：http://localhost:8000/api/v1/health
- RabbitMQ 管理后台：http://localhost:15672（user: guest）
- 前端：http://localhost:5173

## 开发工作流

```bash
# 后端 lint & 类型检查
cd backend
ruff check src && black --check src && isort --check src && mypy src

# 后端测试
pytest tests/ -v

# 前端 lint & 测试
cd frontend
pnpm run lint
pnpm run test
```

## 项目结构

```
├── backend/
│   ├── src/
│   │   ├── api/v1/routers/       # FastAPI 路由层
│   │   ├── application/services/ # 用例/服务层
│   │   ├── domain/               # 实体与仓储接口
│   │   ├── infrastructure/       # DB / MQ / 外部 API 适配
│   │   └── workers/              # Celery 任务
│   ├── alembic/                  # 数据库迁移
│   └── tests/
├── frontend/
│   └── src/
│       ├── pages/                # 页面路由
│       ├── features/             # 业务功能模块
│       └── shared/               # 公共组件/hooks/utils
├── openspec/                     # 架构规范与变更工件
├── docs/                         # 设计文档
├── docker-compose.yml
└── .env.example
```
