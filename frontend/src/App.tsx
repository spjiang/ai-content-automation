import { ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { ReviewConsole } from './features/review/ReviewConsole'

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 6,
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
        },
      }}
    >
      <ReviewConsole />
    </ConfigProvider>
  )
}
