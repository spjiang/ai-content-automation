import {
  CheckCircleOutlined,
  CloudDownloadOutlined,
  FileTextOutlined,
  RedoOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Empty,
  Input,
  Layout,
  Menu,
  message,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { ChangeEvent } from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'

const { Header, Sider, Content } = Layout
const { Title, Paragraph, Text } = Typography

type JobSummary = {
  id: number
  status: string
  canonical_title: string
  topic_fingerprint: string
  asset_version: number
  created_at: string
}

type AssetOut = {
  publish_target: string
  version: number
  title: string
  body: string
  tags: string[]
  cover_text: string | null
  image_suggestions: string[]
}

type JobDetail = JobSummary & {
  prompt_version: string | null
  template_version: string | null
  rule_version: string | null
  failure_code: string | null
  failure_reason: string | null
  assets: AssetOut[]
}

type PackageSummary = {
  id: number
  package_version: string
  created_at: string
}

const api = (path: string) => `/api/v1${path}`

const STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '待审核 (IN_REVIEW)', value: 'IN_REVIEW' },
  { label: '排队 (QUEUED)', value: 'QUEUED' },
  { label: '生成中 (GENERATING)', value: 'GENERATING' },
  { label: '已生成 (GENERATED)', value: 'GENERATED' },
  { label: '已通过 (APPROVED)', value: 'APPROVED' },
  { label: '已打包 (PACKAGED)', value: 'PACKAGED' },
  { label: '待修订 (REVISE_REQUIRED)', value: 'REVISE_REQUIRED' },
  { label: '失败 (FAILED)', value: 'FAILED' },
]

function statusTag(status: string) {
  const colors: Record<string, string> = {
    NEW: 'default',
    QUEUED: 'processing',
    GENERATING: 'processing',
    GENERATED: 'cyan',
    IN_REVIEW: 'warning',
    APPROVED: 'success',
    PACKAGED: 'blue',
    FAILED: 'error',
    REVISE_REQUIRED: 'orange',
  }
  return <Tag color={colors[status] ?? 'default'}>{status}</Tag>
}

export function ReviewConsole() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>('')
  const [jobs, setJobs] = useState<JobSummary[]>([])
  const [jobsLoading, setJobsLoading] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<JobDetail | null>(null)
  const [packages, setPackages] = useState<PackageSummary[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [reviewerId, setReviewerId] = useState('reviewer-1')
  const [rejectReason, setRejectReason] = useState('')

  const loadJobs = useCallback(async () => {
    setJobsLoading(true)
    try {
      const q =
        statusFilter && statusFilter.length > 0
          ? `?status=${encodeURIComponent(statusFilter)}`
          : ''
      const res = await fetch(api(`/jobs${q}`))
      if (!res.ok) {
        message.error(await res.text())
        return
      }
      setJobs(await res.json())
    } finally {
      setJobsLoading(false)
    }
  }, [statusFilter])

  const loadDetail = async (id: number) => {
    setDetailLoading(true)
    try {
      const [jobRes, pkgRes] = await Promise.all([
        fetch(api(`/jobs/${id}`)),
        fetch(api(`/jobs/${id}/packages`)),
      ])
      if (!jobRes.ok) {
        message.error(await jobRes.text())
        return
      }
      setDetail(await jobRes.json())
      if (pkgRes.ok) {
        setPackages(await pkgRes.json())
      } else {
        setPackages([])
      }
    } finally {
      setDetailLoading(false)
    }
  }

  useEffect(() => {
    void loadJobs()
  }, [loadJobs])

  useEffect(() => {
    if (selectedId != null) {
      void loadDetail(selectedId)
    } else {
      setDetail(null)
      setPackages([])
    }
  }, [selectedId])

  const submitReview = async (decision: 'approve' | 'reject') => {
    if (selectedId == null) return
    const res = await fetch(api('/review'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: selectedId,
        decision,
        reviewer_id: reviewerId,
        reject_reason: decision === 'reject' ? rejectReason || null : null,
      }),
    })
    if (!res.ok) {
      message.error(await res.text())
      return
    }
    message.success(decision === 'approve' ? '已通过，已触发打包任务' : '已驳回')
    await loadJobs()
    await loadDetail(selectedId)
  }

  const requeue = async () => {
    if (selectedId == null) return
    const res = await fetch(api(`/jobs/${selectedId}/requeue`), { method: 'POST' })
    if (!res.ok) {
      message.error(await res.text())
      return
    }
    message.success('已重新入队生成')
    await loadJobs()
    await loadDetail(selectedId)
  }

  const triggerPackage = async () => {
    if (selectedId == null) return
    const res = await fetch(api(`/jobs/${selectedId}/package`), { method: 'POST' })
    if (!res.ok) {
      message.error(await res.text())
      return
    }
    message.success('已加入打包队列')
    await loadDetail(selectedId)
  }

  const columns: ColumnsType<JobSummary> = useMemo(
    () => [
      { title: 'ID', dataIndex: 'id', width: 72, fixed: 'left' },
      {
        title: '标题',
        dataIndex: 'canonical_title',
        ellipsis: true,
        render: (t: string) => <Text strong>{t}</Text>,
      },
      {
        title: '状态',
        dataIndex: 'status',
        width: 140,
        render: (s: string) => statusTag(s),
      },
      { title: '资产版本', dataIndex: 'asset_version', width: 96 },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        width: 200,
        render: (v: string) => <Text type="secondary">{v}</Text>,
      },
    ],
    [],
  )

  const tabItems =
    detail?.assets.map((a) => ({
      key: `${a.publish_target}-${a.version}`,
      label: (
        <Space size={4}>
          <FileTextOutlined />
          {a.publish_target === 'douyin_graphic' ? '抖音图文' : '小红书'}
          <Tag>v{a.version}</Tag>
        </Space>
      ),
      children: (
        <div>
          <Title level={5} style={{ marginTop: 0 }}>
            {a.title}
          </Title>
          {a.cover_text ? (
            <Paragraph type="secondary" style={{ marginBottom: 8 }}>
              封面文案：{a.cover_text}
            </Paragraph>
          ) : null}
          <Paragraph style={{ whiteSpace: 'pre-wrap', background: '#fafafa', padding: 12, borderRadius: 8 }}>
            {a.body}
          </Paragraph>
          <Divider orientation="left" plain>
            标签
          </Divider>
          <Space wrap>
            {(a.tags || []).map((tag) => (
              <Tag key={tag}>{tag}</Tag>
            ))}
          </Space>
          <Divider orientation="left" plain>
            配图建议
          </Divider>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {(a.image_suggestions || []).map((s) => (
              <li key={s}>
                <Text>{s}</Text>
              </li>
            ))}
          </ul>
        </div>
      ),
    })) ?? []

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth={64} width={240} theme="dark">
        <div
          style={{
            height: 56,
            margin: 16,
            borderRadius: 8,
            background: 'rgba(255,255,255,0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 600,
            color: '#fff',
            letterSpacing: 0.5,
          }}
        >
          AI 内容运营
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={['review']}
          items={[
            {
              key: 'review',
              icon: <FileTextOutlined />,
              label: '内容审核',
            },
          ]}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            borderBottom: '1px solid #f0f0f0',
            gap: 16,
          }}
        >
          <Breadcrumb
            style={{ flex: 1 }}
            items={[
              { title: '工作台' },
              { title: '内容审核' },
              ...(selectedId ? [{ title: `任务 #${selectedId}` }] : []),
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void loadJobs()}>
            刷新列表
          </Button>
        </Header>
        <Content style={{ margin: 24, minHeight: 360 }}>
          <Row gutter={[16, 16]}>
            <Col xs={24} xl={15}>
              <Card
                title="任务列表"
                extra={
                  <Space wrap>
                    <Select
                      allowClear
                      placeholder="筛选状态"
                      style={{ minWidth: 220 }}
                      value={statusFilter === '' ? undefined : statusFilter}
                      onChange={(v: string | null) => setStatusFilter(v ?? '')}
                      options={STATUS_OPTIONS}
                    />
                  </Space>
                }
              >
                <Table<JobSummary>
                  rowKey="id"
                  loading={jobsLoading}
                  size="middle"
                  pagination={{ pageSize: 10, showSizeChanger: true }}
                  columns={columns}
                  dataSource={jobs}
                  rowClassName={(record: JobSummary) =>
                    record.id === selectedId ? 'ant-table-row-selected' : ''
                  }
                  onRow={(record: JobSummary) => ({
                    onClick: () => setSelectedId(record.id),
                    style: { cursor: 'pointer' },
                  })}
                />
              </Card>
            </Col>
            <Col xs={24} xl={9}>
              <Card title="任务详情" styles={{ body: { minHeight: 420 } }}>
                {selectedId == null && <Empty description="请在左侧表格中选择一条任务" />}
                {selectedId != null && detailLoading && (
                  <div style={{ textAlign: 'center', padding: 48 }}>
                    <Spin tip="加载详情…" />
                  </div>
                )}
                {selectedId != null && !detailLoading && detail && (
                  <>
                    <Space direction="vertical" size={12} style={{ width: '100%' }}>
                      <div>
                        <Title level={4} style={{ marginBottom: 4 }}>
                          {detail.canonical_title}
                        </Title>
                        <Space>{statusTag(detail.status)}</Space>
                      </div>
                      <Descriptions bordered size="small" column={1}>
                        <Descriptions.Item label="任务 ID">{detail.id}</Descriptions.Item>
                        <Descriptions.Item label="资产版本">{detail.asset_version}</Descriptions.Item>
                        <Descriptions.Item label="规则版本">
                          {detail.rule_version ?? '—'}
                        </Descriptions.Item>
                        <Descriptions.Item label="提示词版本">
                          {detail.prompt_version ?? '—'}
                        </Descriptions.Item>
                        <Descriptions.Item label="模板版本">
                          {detail.template_version ?? '—'}
                        </Descriptions.Item>
                        <Descriptions.Item label="话题指纹">
                          <Text copyable ellipsis style={{ maxWidth: 280 }}>
                            {detail.topic_fingerprint}
                          </Text>
                        </Descriptions.Item>
                        {detail.failure_code ? (
                          <Descriptions.Item label="失败信息">
                            <Alert
                              type="error"
                              showIcon
                              message={detail.failure_code}
                              description={detail.failure_reason ?? undefined}
                            />
                          </Descriptions.Item>
                        ) : null}
                      </Descriptions>
                    </Space>

                    <Divider orientation="left">审核操作</Divider>
                    <Space wrap style={{ marginBottom: 12 }}>
                      <Input
                        addonBefore="审核人"
                        value={reviewerId}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setReviewerId(e.target.value)}
                        style={{ width: 260 }}
                      />
                    </Space>
                    {detail.status === 'IN_REVIEW' && (
                      <Space direction="vertical" style={{ width: '100%' }} size="middle">
                        <Space wrap>
                          <Button type="primary" icon={<CheckCircleOutlined />} onClick={() => void submitReview('approve')}>
                            通过
                          </Button>
                          <Button danger onClick={() => void submitReview('reject')}>
                            驳回
                          </Button>
                        </Space>
                        <Input.TextArea
                          rows={3}
                          placeholder="驳回原因（可选）"
                          value={rejectReason}
                          onChange={(e: ChangeEvent<HTMLTextAreaElement>) =>
                            setRejectReason(e.target.value)
                          }
                        />
                      </Space>
                    )}
                    {detail.status === 'REVISE_REQUIRED' && (
                      <Button type="primary" icon={<RedoOutlined />} onClick={() => void requeue()}>
                        重新入队生成
                      </Button>
                    )}
                    {detail.status === 'APPROVED' && (
                      <Button icon={<CloudDownloadOutlined />} onClick={() => void triggerPackage()}>
                        手动触发打包
                      </Button>
                    )}

                    <Divider orientation="left">双平台稿件</Divider>
                    {detail.assets.length === 0 ? (
                      <Empty description="暂无稿件" />
                    ) : (
                      <Tabs items={tabItems} />
                    )}

                    <Divider orientation="left">发布包</Divider>
                    {packages.length === 0 ? (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无发布包" />
                    ) : (
                      <Space direction="vertical" style={{ width: '100%' }}>
                        {packages.map((p) => (
                          <Card key={p.id} size="small" type="inner">
                            <Space>
                              <Tag color="blue">{p.package_version}</Tag>
                              <Text type="secondary">{p.created_at}</Text>
                              <Button
                                type="link"
                                href={api(`/packages/${p.id}/download`)}
                                target="_blank"
                                rel="noreferrer"
                                icon={<CloudDownloadOutlined />}
                              >
                                下载 JSON
                              </Button>
                            </Space>
                          </Card>
                        ))}
                      </Space>
                    )}
                  </>
                )}
              </Card>
            </Col>
          </Row>
        </Content>
      </Layout>
    </Layout>
  )
}
