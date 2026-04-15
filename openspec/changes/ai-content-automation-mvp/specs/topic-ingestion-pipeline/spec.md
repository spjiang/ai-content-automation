## ADDED Requirements

### Requirement: 三源热点并行抓取与原始入库

系统 SHALL 支持微博热搜、知乎热榜、抖音热榜三源并行抓取，并将每次成功抓取结果持久化为 `topic_raw`（平台标识、标题、热度值、链接、抓取时间戳、原始 payload）。

#### Scenario: 单源抓取成功入库

- **WHEN** 某一来源的 collector 返回有效热点条目列表
- **THEN** 系统 SHALL 为每条条目写入一条 `topic_raw` 记录并保留原始 payload 供审计

#### Scenario: 单源失败不阻塞其他源

- **WHEN** 某一来源抓取失败（网络超时、反爬、选择器异常）
- **THEN** 系统 SHALL 仅对该来源执行指数退避重试，其他来源的抓取与入库 SHALL 继续正常执行

#### Scenario: 连续失败触发告警钩子

- **WHEN** 某来源连续失败次数超过配置阈值
- **THEN** 系统 SHALL 触发告警钩子并在日志中记录来源维度的失败统计

### Requirement: 话题归一化与去重排序

系统 SHALL 将 `topic_raw` 归一为 `topic_canonical`（标准标题、聚类键、综合热度、来源集合、去重指纹），并 SHALL 按平台热度归一分、新鲜度衰减与业务偏好权重输出有序话题列表。

#### Scenario: 同话题跨源合并

- **WHEN** 多条 `topic_raw` 在配置时间窗内指纹判定为同一话题
- **THEN** 系统 SHALL 将其合并或关联到同一 `topic_canonical`，并累计来源集合与综合热度

#### Scenario: 支持主题配额控制同质化

- **WHEN** 同类主题候选话题超过配置配额数量
- **THEN** 系统 SHALL 按权重截断至配额上限后再输出给下游规则引擎

### Requirement: 规则引擎过滤与入队

系统 SHALL 对排序后的 `topic_canonical` 列表应用规则（黑白名单、关键词、敏感词、热度阈值），并 SHALL 将通过规则的话题创建 `content_job` 并投递至 Celery/RabbitMQ 生成队列。

#### Scenario: 话题通过规则进入生成队列

- **WHEN** 某 `topic_canonical` 满足所有启用规则且无阻塞性合规问题
- **THEN** 系统 SHALL 创建 `content_job`（状态迁移至 `QUEUED`）并将任务投递至队列

#### Scenario: 规则命中详情可审计与回放

- **WHEN** 规则引擎对任意话题作出入队或丢弃决定
- **THEN** 系统 SHALL 持久化当时生效的规则版本标识与命中明细，以支持后续误杀/漏放回放排查
