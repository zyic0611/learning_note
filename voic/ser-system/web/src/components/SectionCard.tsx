import type { ReactNode } from 'react';

interface SectionCardProps {
  title?: string;
  subtitle?: string;
  extra?: ReactNode;
  children: ReactNode;
  className?: string;
}

export default function SectionCard({ title, subtitle, extra, children, className = '' }: SectionCardProps) {
  return (
    <section className={`section-card ${className}`}>
      {(title || subtitle || extra) && (
        <div className="section-card-head">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {extra && <div className="section-extra">{extra}</div>}
        </div>
      )}
      <div className="section-card-body">{children}</div>
    </section>
  );
}
