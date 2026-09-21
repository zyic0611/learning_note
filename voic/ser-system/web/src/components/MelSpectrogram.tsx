import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

interface MelSpectrogramProps {
  data: number[][];
  duration?: number;
}

export default function MelSpectrogram({ data, duration }: MelSpectrogramProps) {
  const option = useMemo(() => {
    const rows = data.length;
    const columns = Math.max(0, ...data.map((row) => row.length));
    const values: Array<[number, number, number]> = [];
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    data.forEach((row, y) => row.forEach((value, x) => {
      if (!Number.isFinite(value)) return;
      values.push([x, rows - y - 1, value]);
      min = Math.min(min, value);
      max = Math.max(max, value);
    }));
    if (!Number.isFinite(min) || !Number.isFinite(max)) { min = 0; max = 1; }
    if (min === max) max = min + 1;

    return {
      animation: false,
      backgroundColor: 'transparent',
      grid: { left: 44, right: 20, top: 10, bottom: 34 },
      tooltip: {
        trigger: 'item',
        backgroundColor: '#102338',
        borderColor: 'rgba(159,193,218,.22)',
        textStyle: { color: '#edf7fa', fontSize: 12 },
        formatter: (params: unknown) => {
          const [x, y, value] = (params as { data: [number, number, number] }).data;
          const time = columns > 1 && duration ? (x / (columns - 1)) * duration : x;
          return `<strong>${value.toFixed(2)}</strong><br/>时间 ${time.toFixed(2)} s<br/>Mel 频带 ${y + 1}`;
        },
      },
      xAxis: {
        type: 'value', min: 0, max: Math.max(1, columns - 1),
        name: '时间', nameTextStyle: { color: '#748ca1', padding: [10, 0, 0, 0] },
        axisLabel: { color: '#748ca1', formatter: (value: string | number) => {
          const numericValue = Number(value);
          return duration && columns > 1 ? `${((numericValue / (columns - 1)) * duration).toFixed(1)}s` : numericValue.toFixed(0);
        } },
        axisLine: { lineStyle: { color: 'rgba(139,170,192,.24)' } }, splitLine: { show: false }, axisTick: { show: false },
      },
      yAxis: {
        type: 'value', min: 0, max: Math.max(1, rows - 1), name: 'Mel',
        nameTextStyle: { color: '#748ca1' }, axisLabel: { color: '#748ca1' },
        axisLine: { lineStyle: { color: 'rgba(139,170,192,.24)' } }, splitLine: { show: false }, axisTick: { show: false },
      },
      visualMap: {
        min, max, show: false,
        inRange: { color: ['#091725', '#123952', '#116c76', '#1da692', '#78d8c6', '#e0fbf5'] },
      },
      series: [{
        type: 'heatmap', data: values, progressive: 5000,
        emphasis: { itemStyle: { shadowBlur: 4, shadowColor: 'rgba(32,184,166,.45)' } },
      }],
    };
  }, [data, duration]);

  return <ReactECharts option={option} style={{ height: 240, width: '100%' }} notMerge lazyUpdate />;
}
