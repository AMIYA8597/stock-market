import React from 'react';
import { cn } from '@/lib/utils';

const Tooltip = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { content: React.ReactNode; side?: 'top' | 'right' | 'bottom' | 'left' }
>(({ className, content, side = 'top', children, ...props }, ref) => {
  const [isVisible, setIsVisible] = React.useState(false);

  const sideClasses = {
    top: 'bottom-full mb-2',
    right: 'left-full ml-2',
    bottom: 'top-full mt-2',
    left: 'right-full mr-2',
  };

  return (
    <div ref={ref} className="relative inline-block" {...props}>
      <div
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
      >
        {children}
      </div>
      {isVisible && (
        <div
          className={cn(
            'absolute z-50 px-2 py-1 text-xs font-medium rounded whitespace-nowrap',
            'bg-[var(--bg-overlay)] text-[var(--text-primary)] border border-[var(--border-strong)]',
            sideClasses[side],
            className
          )}
        >
          {content}
        </div>
      )}
    </div>
  );
});
Tooltip.displayName = 'Tooltip';

export { Tooltip };
