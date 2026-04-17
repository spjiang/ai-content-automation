# OpenSpec

## 1. 什么是 OpenSpec

`OpenSpec` 是一种把“需求变化”结构化表达和追踪起来的机制。  
它的核心思想不是直接开始写代码，而是先回答这些问题：

- 为什么要做这次变更
- 这次变更新增或修改了什么能力
- 影响哪些模块、边界和约束
- 任务应该如何拆分

在当前项目里，`OpenSpec` 不是抽象概念，而是已经落在仓库目录中的实践。

## 2. 当前项目里的 OpenSpec 工件

你这个仓库里已经能看到比较典型的 `OpenSpec` 结构：

- `openspec/changes/ai-content-automation-mvp/proposal.md`
- `openspec/changes/ai-content-automation-mvp/tasks.md`
- `openspec/changes/ai-content-automation-mvp/specs/review-and-publish-package/spec.md`
- `openspec/config.yaml`

从这些文件的职责看，可以这样理解：

- `proposal.md`：说明为什么要做、做哪些变化、影响范围是什么
- `spec.md`：把能力要求写成更明确、更接近验收标准的规格
- `tasks.md`：把工作拆成可以执行和跟踪的任务
- `config.yaml`：给整个项目设定统一技术栈、架构和约束背景

## 3. 它在当前项目里起什么作用

### 3.1 把“想法”变成“变更定义”

例如在 `ai-content-automation-mvp` 里，项目目标不是泛泛地说“做个 AI 内容系统”，而是被明确成：

- 三源热点抓取
- 规则过滤与入队
- DeepSeek 双平台图文生成
- 人工审核
- 发布包导出
- MVP 不做自动发布、不做短视频生成

这就是 `OpenSpec` 的第一层价值：收敛范围。

### 3.2 把“能力说明”变成“可追踪工件”

以 `review-and-publish-package/spec.md` 为例，文档中已经把审核流、版本链、发布包导出、可空业务字段写成了要求和场景。  
这意味着后续实现和验证时，不需要重新猜“需求原意是什么”。

### 3.3 把“实现计划”变成“任务序列”

`tasks.md` 把工作拆成 `M1`、`M2`、`M3`，并分到更细的条目。  
这样做的意义是：

- 开发者知道先做什么、后做什么
- 管理者能追踪阶段进度
- AI 可以基于任务颗粒度参与实现，而不是一次吞掉全部范围

## 4. 它和普通需求文档有什么不同

普通需求文档经常偏业务描述，但对工程落地不够友好。  
`OpenSpec` 更强调“变更可执行性”，也就是：

- 要写清楚影响范围
- 要明确能力边界
- 要能衔接实现与验证
- 要能支持持续迭代

换句话说，`OpenSpec` 不是只给产品看，也不是只给开发看，而是给整个交付流程看。

## 5. 当前仓库里最值得关注的 OpenSpec 信号

### 5.1 `proposal.md` 负责说明“为什么做”

在当前仓库里，`proposal.md` 已经说明了：

- 业务痛点是什么
- MVP 解决什么问题
- 哪些能力是新增
- 哪些事情明确不做

这类信息对管理者很关键，因为它决定了范围控制是否清晰。

### 5.2 `spec.md` 负责说明“做到什么程度算完成”

例如审核 API、状态迁移、版本化发布包、失败可重试等要求，都属于可以直接转成实现和验收的规格。  
它比单纯的“做审核功能”更具体。

### 5.3 `tasks.md` 负责说明“工作怎么拆”

像 `M1`、`M2`、`M3` 这种里程碑式拆分，非常适合做项目推进与阶段跟踪。  
开发者看的是执行顺序，管理者看的是交付路径。

### 5.4 `config.yaml` 负责说明“变更不能脱离什么背景”

当前 `openspec/config.yaml` 已经写了：

- 后端是 `Python 3.11 + FastAPI`
- 前端是 `React + TypeScript + Vite`
- 数据库是 `PostgreSQL`
- 异步任务是 `Celery + RabbitMQ`
- 路由规范是 `/api/v1`
- Schema 变更走 `Alembic`

这类配置让规格不是悬空的，而是和真实工程上下文绑定。

## 6. 对开发者的实际价值

开发者在开始写实现前，应该先用 `OpenSpec` 搞清楚三件事：

- 本次变更到底要交付哪些能力
- 哪些属于范围内，哪些明确不做
- 哪些技术和架构约束不能违背

如果没有这一步，就很容易发生：

- 功能做多了，超出 MVP
- 功能做偏了，和规格不一致
- 技术实现和项目基线冲突

## 7. 对管理者的实际价值

管理者用 `OpenSpec`，主要不是看代码细节，而是看交付是否可控：

- 有没有先定义变化，再开始实施
- 每个变更是否有明确目标和边界
- 任务拆分是否足够支撑排期与跟踪
- 风险、影响和范围是否有文档依据

这让项目管理从“问开发进度”转向“看变更工件是否闭环”。

## 8. 适用场景

`OpenSpec` 特别适合这些场景：

- 需求会持续变化的项目
- 需要多人协作的中长期项目
- 有架构约束和质量门禁的系统
- 希望 AI 协作不是随意发挥，而是基于规格执行

对小型一次性脚本来说，它可能显得偏重；  
但对当前这种自动化内容系统，它非常合适。

## 9. 和另外三个点的边界

### 9.1 它不是 Harness Engineering

`Harness Engineering` 是总方法，`OpenSpec` 是其中负责“变更规格”的组件。

### 9.2 它不是 Superpower

`OpenSpec` 负责定义“做什么”；  
`Superpower` 负责规定 AI “怎么按流程完成”。

### 9.3 它不是 Cursor Rule

`OpenSpec` 是变更级工件；  
`Cursor Rule` 是仓库级长期规则。

## 10. 学这个项目时的建议抓手

如果你要从当前仓库深入理解 `OpenSpec`，建议按下面顺序读：

1. `openspec/changes/ai-content-automation-mvp/proposal.md`
2. `openspec/changes/ai-content-automation-mvp/specs/review-and-publish-package/spec.md`
3. `openspec/changes/ai-content-automation-mvp/tasks.md`
4. `openspec/config.yaml`

这样你会从“为什么做”一路看到“做什么”“怎么拆”“受什么约束”。

## 11. 一句话记忆

在当前项目里，`OpenSpec` 的作用就是：  
把需求变化从“聊天里的想法”，变成“可执行、可追踪、可验证的工程规格”。
