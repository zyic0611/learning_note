import { Layout, Menu, Tooltip } from 'antd';
import { Activity, AudioLines, ChartNoAxesCombined, FileAudio2, FlaskConical, RefreshCw } from 'lucide-react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useHealth } from '../hooks/useHealth';

const { Sider, Content } = Layout;

const NAV_ITEMS = [
  { key: '/realtime', icon: <AudioLines size={18} />, label: '实时识别' },
  { key: '/analysis', icon: <FileAudio2 size={18} />, label: '音频分析' },
  { key: '/evaluation', icon: <ChartNoAxesCombined size={18} />, label: '模型评估' },
];

export default function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const health = useHealth();
  const healthLabel = health.state === 'online'
    ? '推理服务在线'
    : health.state === 'offline' && health.detail
      ? `模型${health.detail.model_ready ? '就绪' : '未就绪'} · 转写${health.detail.asr_ready ? '就绪' : '未就绪'}`
      : health.state === 'offline' ? '推理服务离线' : '正在检查服务';

  return (
    <Layout className="app-shell">
      <Sider width={232} className="app-sider" breakpoint="lg" collapsedWidth={72}>
        <div className="brand">
          <div className="brand-mark" aria-hidden="true"><Activity size={22} strokeWidth={2.3} /></div>
          <div className="brand-copy">
            <strong>声析</strong>
            <span>Speech Emotion Lab</span>
          </div>
        </div>
        <div className="nav-section-label">研究工作台</div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={NAV_ITEMS}
          onClick={({ key }) => navigate(key)}
          className="app-menu"
        />
        <div className="sider-footer">
          <div className="research-badge"><FlaskConical size={15} /><span>From-scratch CNN</span></div>
          <div className="sider-caption">六分类中文语音情感识别</div>
        </div>
      </Sider>
      <Layout className="main-plane">
        <header className="topbar">
          <div className="topbar-context">
            <span className="eyebrow">SER Research Console</span>
            <span className="topbar-separator" />
            <span className="topbar-note">16 kHz · 单声道 · PCM16</span>
          </div>
          <Tooltip title={health.state === 'offline' ? '点击重试健康检查' : health.detail?.model ?? healthLabel}>
            <button type="button" className={`health-pill health-${health.state}`} onClick={() => void health.refresh()}>
              <span className="status-dot" />
              <span>{healthLabel}</span>
              {health.state === 'offline' && <RefreshCw size={13} />}
            </button>
          </Tooltip>
        </header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
