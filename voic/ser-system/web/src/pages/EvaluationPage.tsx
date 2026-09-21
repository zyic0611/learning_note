import { useCallback, useEffect, useState } from 'react';
import { Button, Table, Tag } from 'antd';
import { Award, BarChart3, CheckCircle2, Database, FlaskConical, GitCompareArrows, RefreshCw, ShieldCheck, UsersRound } from 'lucide-react';
import { getMetrics } from '../api/client';
import ConfusionMatrix from '../components/ConfusionMatrix';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import StatePanel from '../components/StatePanel';
import type { FoldMetric, MetricsResponse, ModelComparisonRow } from '../types/api';
import { formatMetric } from '../utils/format';

export default function EvaluationPage() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [state, setState] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState('');

  const load = useCallback(async (signal?: AbortSignal) => {
    setState('loading');
    setError('');
    try {
      const response = await getMetrics(signal);
      setMetrics(response);
      setState('success');
    } catch (loadError) {
      if (loadError instanceof DOMException && loadError.name === 'AbortError') return;
      setError(loadError instanceof Error ? loadError.message : '无法加载评估指标。');
      setState('error');
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const comparisonColumns = [
    { title: '模型', dataIndex: 'model', key: 'model', render: (value: string, _row: ModelComparisonRow, index: number) => <div className="model-name"><span className={index === 0 || /cnn/i.test(value) ? 'model-dot model-primary' : 'model-dot'} /> <strong>{value}</strong>{(index === 0 || /cnn/i.test(value)) && <Tag bordered={false} color="cyan">本文模型</Tag>}</div> },
    { title: 'UAR', dataIndex: 'uar', key: 'uar', align: 'right' as const, render: (value: number) => <span className="metric-cell">{formatMetric(value)}</span> },
    { title: 'Macro F1', dataIndex: 'macroF1', key: 'macroF1', align: 'right' as const, render: (value: number) => <span className="metric-cell">{formatMetric(value)}</span> },
    { title: 'Accuracy', dataIndex: 'accuracy', key: 'accuracy', align: 'right' as const, render: (value: number) => <span className="metric-cell">{formatMetric(value)}</span> },
    { title: '参数量', dataIndex: 'parameters', key: 'parameters', align: 'right' as const, render: (value?: string | number) => value ?? '—' },
  ];

  const foldColumns = [
    { title: '折次', dataIndex: 'fold', key: 'fold', render: (value: string) => <strong>{value}</strong> },
    { title: 'UAR', dataIndex: 'uar', key: 'uar', align: 'right' as const, render: (value: number) => formatMetric(value) },
    { title: 'Macro F1', dataIndex: 'macroF1', key: 'macroF1', align: 'right' as const, render: (value: number) => formatMetric(value) },
    { title: 'Accuracy', dataIndex: 'accuracy', key: 'accuracy', align: 'right' as const, render: (value: number) => formatMetric(value) },
    { title: '训练样本', dataIndex: 'trainSamples', key: 'trainSamples', align: 'right' as const, render: (value?: number) => value ?? '—' },
    { title: '测试样本', dataIndex: 'testSamples', key: 'testSamples', align: 'right' as const, render: (value?: number) => value ?? '—' },
  ];

  return (
    <main className="page-stack evaluation-page">
      <PageHeader
        eyebrow="Model Benchmark"
        title="模型评估"
        description="查看主模型的交叉验证表现、基线对比与分类混淆，所有指标均来自独立说话人测试折。"
        actions={<Button icon={<RefreshCw size={15} />} onClick={() => void load()} loading={state === 'loading'}>刷新指标</Button>}
      />

      {state === 'loading' && !metrics && <StatePanel kind="loading" title="正在加载评估数据" description="从指标服务读取交叉验证与混淆矩阵。" />}
      {state === 'error' && !metrics && <StatePanel kind="error" title="评估数据加载失败" description={error} onRetry={() => void load()} />}

      {metrics && (
        <div className={state === 'loading' ? 'is-refetching' : ''}>
          <div className="method-callout">
            <div className="method-icon"><ShieldCheck size={25} /></div>
            <div><span>Evaluation Protocol</span><strong>说话人完全独立的 5 折交叉验证</strong><p>同一说话人的样本不会同时出现在训练集与测试集；CNN 从随机初始化开始训练，不使用预训练声学模型。</p></div>
            <div className="method-chips"><span><UsersRound size={14} />Speaker-disjoint</span><span><FlaskConical size={14} />From scratch</span></div>
          </div>

          <div className="kpi-grid">
            <article className="kpi-card kpi-primary"><div className="kpi-icon"><Award size={20} /></div><div><span>UAR</span><strong>{formatMetric(metrics.uar)}</strong><p>六类召回率的非加权均值</p></div></article>
            <article className="kpi-card"><div className="kpi-icon"><BarChart3 size={20} /></div><div><span>Macro F1</span><strong>{formatMetric(metrics.macroF1)}</strong><p>各类别 F1 的宏平均</p></div></article>
            <article className="kpi-card"><div className="kpi-icon"><CheckCircle2 size={20} /></div><div><span>Accuracy</span><strong>{formatMetric(metrics.accuracy)}</strong><p>全部测试样本整体准确率</p></div></article>
            <article className="kpi-card kpi-context"><div className="kpi-icon"><Database size={20} /></div><div><span>评估样本</span><strong>{metrics.sampleCount?.toLocaleString() ?? '—'}</strong><p>{metrics.dataset ?? '测试集汇总'}</p></div></article>
          </div>

          <div className="evaluation-grid">
            <SectionCard title="模型基线对比" subtitle="CNN 主模型与传统 SVM 基线在相同划分上的表现" extra={<GitCompareArrows size={18} />}>
              {metrics.comparison.length > 0 ? (
                <Table<ModelComparisonRow> rowKey="model" pagination={false} size="middle" dataSource={metrics.comparison} columns={comparisonColumns} scroll={{ x: 640 }} />
              ) : <StatePanel kind="empty" title="暂无模型对比数据" description="接口未返回 comparison 字段。" />}
            </SectionCard>

            <SectionCard title="六分类混淆矩阵" subtitle="行表示真实类别，列表示预测类别；每行归一化为 100%">
              {metrics.confusionMatrix.length >= 6 ? (
                <ConfusionMatrix matrix={metrics.confusionMatrix} labels={metrics.labels} />
              ) : <StatePanel kind="empty" title="暂无混淆矩阵" description="接口需返回 6 × 6 数值矩阵。" />}
            </SectionCard>
          </div>

          <SectionCard title="各折评估明细" subtitle="每折的测试说话人与其余训练说话人严格隔离" extra={<Tag bordered={false}>5-FOLD CV</Tag>}>
            {metrics.folds.length > 0 ? (
              <Table<FoldMetric> rowKey="fold" pagination={false} size="middle" dataSource={metrics.folds} columns={foldColumns} scroll={{ x: 680 }} summary={(data) => {
                const mean = (key: 'uar' | 'macroF1' | 'accuracy') => data.reduce((sum, row) => sum + row[key], 0) / Math.max(1, data.length);
                return <Table.Summary.Row className="fold-summary"><Table.Summary.Cell index={0}><strong>平均</strong></Table.Summary.Cell><Table.Summary.Cell index={1} align="right"><strong>{formatMetric(mean('uar'))}</strong></Table.Summary.Cell><Table.Summary.Cell index={2} align="right"><strong>{formatMetric(mean('macroF1'))}</strong></Table.Summary.Cell><Table.Summary.Cell index={3} align="right"><strong>{formatMetric(mean('accuracy'))}</strong></Table.Summary.Cell><Table.Summary.Cell index={4} /><Table.Summary.Cell index={5} /></Table.Summary.Row>;
              }} />
            ) : <StatePanel kind="empty" title="暂无折次明细" description="接口未返回 folds 字段。" />}
          </SectionCard>
        </div>
      )}
    </main>
  );
}
