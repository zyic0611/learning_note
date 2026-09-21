import { AlertCircle, Database, LoaderCircle } from 'lucide-react';
import { Button } from 'antd';

interface StatePanelProps {
  kind: 'loading' | 'error' | 'empty';
  title: string;
  description?: string;
  onRetry?: () => void;
}

export default function StatePanel({ kind, title, description, onRetry }: StatePanelProps) {
  const Icon = kind === 'loading' ? LoaderCircle : kind === 'error' ? AlertCircle : Database;
  return (
    <div className={`state-panel state-${kind}`}>
      <Icon size={25} className={kind === 'loading' ? 'spin' : ''} />
      <strong>{title}</strong>
      {description && <p>{description}</p>}
      {onRetry && <Button onClick={onRetry}>重新加载</Button>}
    </div>
  );
}
