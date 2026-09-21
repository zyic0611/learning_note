import { useMemo, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Table } from 'antd';
import { EMOTION_MAP } from '../constants/emotions';
import type { EmotionKey } from '../types/api';
import { normalizeScore } from '../utils/format';

interface ConfusionMatrixProps {
  matrix: number[][];
  labels: EmotionKey[];
}

export default function ConfusionMatrix({ matrix, labels }: ConfusionMatrixProps) {
  const [view, setView] = useState<'chart' | 'table'>('chart');
  const normalized = useMemo(() => matrix.slice(0, 6).map((row) => {
    const values = row.slice(0, 6).map((value) => Math.max(0, Number(value) || 0));
    const sum = values.reduce((total, value) => total + value, 0);
    if (sum > 0) return values.map((value) => value / sum);
    return values.map(normalizeScore);
  }), [matrix]);

  const names = labels.map((label) => EMOTION_MAP[label].label);
  const option = useMemo(() => ({
    animationDuration: 450,
    backgroundColor: 'transparent',
    grid: { left: 68, right: 24, top: 22, bottom: 58 },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#102338', borderColor: 'rgba(159,193,218,.22)', textStyle: { color: '#edf7fa' },
      formatter: (params: unknown) => {
        const [predicted, actual, value] = (params as { data: [number, number, number] }).data;
        return `<strong>${(value * 100).toFixed(1)}%</strong><br/>真实：${names[actual]}<br/>预测：${names[predicted]}`;
      },
    },
    xAxis: {
      type: 'category', data: names, name: '预测类别', nameLocation: 'middle', nameGap: 38,
      nameTextStyle: { color: '#8ba2b5' }, axisLabel: { color: '#9eb3c5', interval: 0 },
      axisTick: { show: false }, axisLine: { lineStyle: { color: 'rgba(139,170,192,.24)' } },
    },
    yAxis: {
      type: 'category', data: names, inverse: true, name: '真实类别', nameLocation: 'middle', nameGap: 51,
      nameTextStyle: { color: '#8ba2b5' }, axisLabel: { color: '#9eb3c5', interval: 0 },
      axisTick: { show: false }, axisLine: { lineStyle: { color: 'rgba(139,170,192,.24)' } },
    },
    visualMap: {
      min: 0, max: 1, orient: 'horizontal', left: 'center', bottom: 2, itemWidth: 130, itemHeight: 8,
      text: ['高', '低'], textStyle: { color: '#748ca1', fontSize: 11 },
      inRange: { color: ['#102238', '#123b53', '#116f78', '#20a794', '#73d8c8', '#dcfaf4'] },
      calculable: false,
    },
    series: [{
      name: '混淆矩阵', type: 'heatmap',
      data: normalized.flatMap((row, actual) => row.map((value, predicted) => [predicted, actual, value])),
      label: { show: true, formatter: (params: unknown) => `${(((params as { data: [number, number, number] }).data[2]) * 100).toFixed(0)}%`, color: '#edf7fa', fontSize: 11 },
      itemStyle: { borderColor: '#102338', borderWidth: 2, borderRadius: 3 },
      emphasis: { itemStyle: { shadowBlur: 7, shadowColor: 'rgba(32,184,166,.4)' } },
    }],
  }), [names, normalized]);

  const tableData = names.map((actual, rowIndex) => ({
    key: actual,
    actual,
    ...Object.fromEntries(names.map((name, columnIndex) => [name, normalized[rowIndex]?.[columnIndex] ?? 0])),
  }));

  return (
    <div className="matrix-wrap">
      <div className="chart-view-toggle" role="group" aria-label="混淆矩阵视图">
        <button type="button" className={view === 'chart' ? 'is-active' : ''} onClick={() => setView('chart')}>热力图</button>
        <button type="button" className={view === 'table' ? 'is-active' : ''} onClick={() => setView('table')}>数据表</button>
      </div>
      {view === 'chart' ? (
        <ReactECharts option={option} style={{ height: 390, width: '100%' }} notMerge lazyUpdate />
      ) : (
        <Table
          size="small"
          pagination={false}
          scroll={{ x: 630 }}
          dataSource={tableData}
          columns={[
            { title: '真实 / 预测', dataIndex: 'actual', fixed: 'left', width: 110 },
            ...names.map((name) => ({ title: name, dataIndex: name, align: 'right' as const, render: (value: number) => `${(value * 100).toFixed(1)}%` })),
          ]}
        />
      )}
    </div>
  );
}
