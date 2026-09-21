import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#20b8a6',
          colorInfo: '#3987e5',
          colorSuccess: '#2bb789',
          colorWarning: '#dca543',
          colorError: '#e66767',
          colorBgBase: '#081420',
          colorBgContainer: '#102338',
          colorBgElevated: '#142b43',
          colorBorder: 'rgba(159, 193, 218, 0.16)',
          colorText: '#edf7fa',
          colorTextSecondary: '#9eb3c5',
          borderRadius: 10,
          borderRadiusLG: 14,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
          controlHeight: 38,
        },
        components: {
          Card: { paddingLG: 20 },
          Table: { headerBg: 'rgba(12, 31, 49, 0.72)', rowHoverBg: 'rgba(32, 184, 166, 0.06)' },
          Menu: { darkItemBg: 'transparent', darkItemSelectedBg: 'rgba(32, 184, 166, 0.14)', darkItemSelectedColor: '#62ddd0' },
          Button: { primaryShadow: 'none' },
        },
      }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>,
);
