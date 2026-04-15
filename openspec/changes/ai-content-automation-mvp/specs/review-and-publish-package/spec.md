## ADDED Requirements

### Requirement: 人工审核流与版本链

系统 SHALL 提供审核 API，审核人可对处于 `IN_REVIEW` 状态的内容给出通过或驳回结论；系统 SHALL 将审核记录持久化为 `review_record`（审核人、结论、驳回原因、修改意见、版本号）。

#### Scenario: 审核通过状态迁移

- **WHEN** 审核人通过 API 对某 `content_job` 给出通过结论
- **THEN** 系统 SHALL 写入 `review_record` 并将任务状态迁移至 `APPROVED`

#### Scenario: 审核驳回进入修订态并保留版本链

- **WHEN** 审核人给出驳回结论并附驳回原因
- **THEN** 系统 SHALL 写入 `review_record` 并将任务置于 `REVISE_REQUIRED`，且 SHALL 保留完整历史版本链以支持后续重新入队与对比

#### Scenario: 修订后重新入队

- **WHEN** 处于 `REVISE_REQUIRED` 的任务被操作重新入队
- **THEN** 系统 SHALL 创建新版本 `content_asset`（不覆盖旧版），任务状态迁移回 `QUEUED`

### Requirement: 版本化发布包导出

系统 SHALL 在审核通过（`APPROVED`）后生成 `publish_package`（结构化 JSON 或 zip、版本号、生成时间、有效期、预留 `download_url` 字段），状态迁移至 `PACKAGED`；MVP 阶段 SHALL NOT 调用平台自动发布 API。

#### Scenario: 审核通过后生成版本化发布包

- **WHEN** 打包任务成功执行
- **THEN** 系统 SHALL 创建带唯一版本号的 `publish_package`，状态迁移至 `PACKAGED`，且同一逻辑版本 SHALL NOT 被静默覆盖

#### Scenario: 打包失败可重试且不丢资产

- **WHEN** 打包任务失败
- **THEN** 系统 SHALL 保留已审核通过的 `content_asset`，并 SHALL 允许在故障恢复后重新打包生成新版本 `publish_package`

### Requirement: 业务效果回填字段预留

系统 SHALL 在 `publish_package` 或关联模型中预留人工可填写的业务效果字段（曝光量、播放量、互动量、CTR），允许为空；不得因字段为空而影响发布包的正常生成与导出。

#### Scenario: 发布包包含可空效果字段

- **WHEN** 读取或下载任意 `publish_package`
- **THEN** 返回数据结构 SHALL 包含约定的效果字段，字段值允许为 null 且不影响导出完整性
