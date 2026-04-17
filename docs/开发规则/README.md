# 开发规则总览：Harness Engineering、OpenSpec、Superpower、Cursor Rule

## 1. 为什么要学这四个点

在这个项目里，AI 不是单独拿来“写几行代码”的工具，而是被放进了一套更完整的研发流程里。  
如果只懂提示词，不理解规格、规则、技能和工程治理之间的关系，就很容易出现下面几类问题：

- 需求说不清，AI 直接开始写，结果方向跑偏
- 写出来的代码和项目约束不一致，后面返工
- 文档、任务、实现、验证之间断层，管理者很难判断进度是否真实
- 团队成员各自用各自的方法与 AI 协作，最终流程不可复制

这四个技术点，正好对应了 AI 工程化落地里的四个层面：

- `Harness Engineering`：工程方法与协作框架
- `OpenSpec`：需求与变更规格管理
- `Superpower`：AI 工作流技能体系
- `Cursor Rule`：AI 行为约束与项目规则

一句话理解：

`Harness Engineering` 决定“团队怎样把 AI 纳入研发体系”；  
`OpenSpec` 决定“需求变更如何被定义和追踪”；  
`Superpower` 决定“AI 在不同任务里应该按什么流程做事”；  
`Cursor Rule` 决定“AI 在当前仓库里必须遵守哪些硬约束”。

## 2. 四者的本质区别

| 技术点 | 本质 | 主要回答的问题 | 在当前项目中的体现 |
| --- | --- | --- | --- |
| `Harness Engineering` | 工程方法论 | 怎么把 AI 变成可控的研发生产力 | 当前项目整体工作方式本身 |
| `OpenSpec` | 规格与变更管理机制 | 为什么做、做什么、影响什么、任务如何拆分 | `openspec/changes/`、`openspec/config.yaml` |
| `Superpower` | AI 执行流程技能库 | AI 应该先思考什么、再做什么、如何验证 | `brainstorming`、`writing-plans`、`verification-before-completion` 等 |
| `Cursor Rule` | 仓库级行为约束 | AI 在此仓库中哪些能做、哪些不能做 | `.cursor/rules/*.mdc` |

可以把它们理解成不同层级：

- 最外层是 `Harness Engineering`，它是整体打法
- 中间层是 `OpenSpec` 和 `Superpower`
- 最内层是 `Cursor Rule`，它直接约束当前会话里的执行行为

## 3. 在本项目里的分工

### 3.1 Harness Engineering 的角色

本项目虽然没有单独出现一个叫 `Harness Engineering` 的目录，但整个协作方式已经具备它的特征：

- 先做需求澄清，再做设计，再实施，再验证
- 用结构化工件承接讨论结果，而不是只靠聊天记录
- 让 AI 参与方案、计划、实现、验证多个阶段
- 用规则和规格限制 AI 的输出边界

这正是一种典型的 AI 工程化协作模式。

### 3.2 OpenSpec 的角色

`OpenSpec` 在这个项目里承担“变更与规格中台”的作用。  
从仓库内容看，已经有比较清晰的工件链路：

- `openspec/changes/ai-content-automation-mvp/proposal.md`
- `openspec/changes/ai-content-automation-mvp/tasks.md`
- `openspec/changes/ai-content-automation-mvp/specs/review-and-publish-package/spec.md`
- `openspec/config.yaml`

这说明项目不是“想到哪写到哪”，而是先把变更目的、能力说明、任务拆解写清楚，再进入实施。

### 3.3 Superpower 的角色

`Superpower` 更像 AI 的“工作方法插件”。  
它不直接代表业务需求，而是规定 AI 在执行任务时的过程，比如：

- 先用 `brainstorming` 做需求探索与方案设计
- 再用 `writing-plans` 把设计转成实施计划
- 完成前用 `verification-before-completion` 做验证

也就是说，`OpenSpec` 解决“做什么”，`Superpower` 解决“怎么做”。

### 3.4 Cursor Rule 的角色

`.cursor/rules` 是当前仓库给 AI 设置的长期约束。  
例如你这个项目里已经明确规定：

- 需求或范围变化时要先更新 OpenSpec 工件
- 后端基于 Python 3.11、FastAPI、PostgreSQL、Alembic
- 长耗时任务要走 Celery + RabbitMQ
- 禁止硬编码密钥
- 提交前应做 lint/test

这些不是“建议”，而是仓库级规范。AI 在当前项目里工作时，必须优先考虑这些约束。

## 4. 一个完整的协作顺序

如果把这四者串起来，本项目比较理想的工作顺序是：

1. 用 `Harness Engineering` 的思路定义整体协作方式  
   先明确这不是随意对话，而是规范化研发流程
2. 用 `OpenSpec` 描述变更  
   例如写 `proposal`、`spec`、`tasks`
3. 用 `Superpower` 驱动 AI 按流程执行  
   例如先头脑风暴，再写计划，再实施，再验证
4. 用 `Cursor Rule` 持续约束执行细节  
   确保输出不偏离技术栈、安全要求、质量门禁

所以它们不是并列替代关系，而是协同关系。

## 5. 开发者应该重点关注什么

- 看 `OpenSpec`，先理解本次变更到底要交付什么
- 看 `Superpower`，理解 AI 这次应该按什么流程参与
- 看 `Cursor Rule`，避免实现偏离仓库规范
- 从 `Harness Engineering` 视角思考：本次工作是否可复用、可验证、可回溯

对开发者来说，核心不是“会不会提问 AI”，而是“能不能让 AI 在可控流程里稳定产出”。

## 6. 管理者应该重点关注什么

- 是否先有规格再有实现，而不是直接编码
- 是否能从 `OpenSpec` 工件看到范围、风险、任务和边界
- 是否通过 `Cursor Rule` 把关键治理要求固化
- 是否通过 `Superpower` 让 AI 协作方式可重复、可培训、可审计

对管理者来说，关键不是 AI 写得多快，而是：

- 交付是否可追踪
- 结果是否可信
- 过程是否可复制
- 风险是否被前置控制

## 7. 最容易混淆的几点

### 7.1 OpenSpec 和 Cursor Rule 不是一回事

- `OpenSpec` 管的是“本次变更要做什么”
- `Cursor Rule` 管的是“无论做什么，都要遵守哪些长期规则”

前者偏“变更级”，后者偏“仓库级”。

### 7.2 Superpower 和 Cursor Rule 不是一回事

- `Superpower` 更像流程技能，告诉 AI 先后步骤
- `Cursor Rule` 更像边界条件，告诉 AI 什么能做、什么不能做

前者偏“方法”，后者偏“约束”。

### 7.3 Harness Engineering 不是某一个具体文件

它更像上位概念。  
你可以把它理解成：把 `OpenSpec`、`Superpower`、`Cursor Rule` 这些能力，组合成一套真正能落地的 AI 研发协作体系。

## 8. 针对当前仓库的建议理解方式

如果你要真正学会这四个点，建议按下面顺序看：

1. 先看本文件，建立整体认知
2. 再看 `02-OpenSpec.md`，理解这个项目如何做需求和变更管理
3. 再看 `03-Superpower.md`，理解 AI 在这里如何被组织起来工作
4. 再看 `04-Cursor-Rule.md`，理解仓库规范如何约束 AI 与开发者
5. 最后看 `01-Harness-Engineering.md`，从更高层总结这套方法为什么成立

## 9. 一句话总结

在当前项目里：

- `Harness Engineering` 是总方法
- `OpenSpec` 是变更规格系统
- `Superpower` 是 AI 工作流系统
- `Cursor Rule` 是执行约束系统

四者结合起来，目标不是“让 AI 更会写代码”，而是“让 AI 参与的软件交付变得更可控、更稳定、更可管理”。
