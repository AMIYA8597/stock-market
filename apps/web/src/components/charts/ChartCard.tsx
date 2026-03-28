import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

interface ChartCardProps {
  title: string;
  subtitle?: string;
  className?: string;
  contentClassName?: string;
  children: React.ReactNode;
}

export function ChartCard({ title, subtitle, className, contentClassName, children }: ChartCardProps): JSX.Element {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-[var(--nq-text-secondary)]">{title}</CardTitle>
        {subtitle ? <p className="text-xs text-[var(--nq-text-tertiary)]">{subtitle}</p> : null}
      </CardHeader>
      <CardContent className={contentClassName}>{children}</CardContent>
    </Card>
  );
}
