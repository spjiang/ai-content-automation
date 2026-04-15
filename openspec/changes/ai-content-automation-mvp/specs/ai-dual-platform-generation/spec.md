## ADDED Requirements

### Requirement: DeepSeek 双平台图文稿件生成

系统 SHALL 由 Celery worker 消费生成队列中的 `content_job`，调用 DeepSeek 生成抖音图文版与小红书版两条 `content_asset`（含标题、正文、标签、封面文案、配图建议）。

#### Scenario: 生成成功写入双平台资产

- **WHEN** worker 取出可执行的 `content_job` 且 DeepSeek 返回有效内容
- **THEN** 系统 SHALL 将 `content_job` 状态迁移至 `GENERATED` 并写入或更新对应两条 `content_asset` 记录

#### Scenario: 生成失败分类并标记可重试

- **WHEN** DeepSeek 调用失败（超时、限流、内容安全拒绝、模板渲染异常等任一原因）
- **THEN** 系统 SHALL 将失败类型写入 `content_job.failure_reason`，并 SHALL 根据错误类型设置可自动重试或需人工介入的标记，状态迁移至 `FAILED`

### Requirement: 提示词与模板版本化记录

系统 SHALL 在每次生成任务执行时，将当时使用的提示词版本标识与平台模板版本标识持久化至 `content_job`。

#### Scenario: 任务携带版本元数据

- **WHEN** worker 开始执行一条 `content_job`
- **THEN** 系统 SHALL 将规则版本、提示词版本、平台模板版本写入该任务记录，且后续不得被覆盖

### Requirement: 生成任务幂等与重入队

系统 SHALL 保证同一 `content_job` 被多次消费（因网络重投或手动重试）时不产生重复的 `content_asset` 数据；手动重试 SHALL 支持生成新版本资产并保留版本链。

#### Scenario: 重复消费不产生冗余资产

- **WHEN** 同一 `content_job` 消息被 worker 重复消费
- **THEN** 系统 SHALL 幂等处理，不创建多余的 `content_asset` 行，且任务最终状态唯一
