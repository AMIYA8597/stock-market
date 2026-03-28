import React from 'react';
import { cn } from '@/lib/utils';

interface TabsContextValue {
  value: string;
  setValue: (value: string) => void;
}

const TabsContext = React.createContext<TabsContextValue | null>(null);

interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue: string;
  onValueChange?: (value: string) => void;
}

interface TabsListProps extends React.HTMLAttributes<HTMLDivElement> {}

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

function useTabsContext(): TabsContextValue {
  const context = React.useContext(TabsContext);
  if (!context) {
    throw new Error('Tabs components must be used within Tabs');
  }
  return context;
}

const Tabs = React.forwardRef<HTMLDivElement, TabsProps>(
  ({ className, defaultValue, onValueChange, children, ...props }, ref) => {
    const [value, setValue] = React.useState(defaultValue);

    const handleValueChange = React.useCallback(
      (newValue: string) => {
        setValue(newValue);
        onValueChange?.(newValue);
      },
      [onValueChange]
    );

    return (
      <TabsContext.Provider value={{ value, setValue: handleValueChange }}>
        <div ref={ref} className={cn('w-full', className)} {...props}>
          {children}
        </div>
      </TabsContext.Provider>
    );
  }
);
Tabs.displayName = 'Tabs';

const TabsList = React.forwardRef<HTMLDivElement, TabsListProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'inline-flex h-10 items-center justify-center rounded-md bg-[var(--bg-elevated)] p-1',
        'border border-[var(--border-subtle)]',
        className
      )}
      {...props}
    />
  )
);
TabsList.displayName = 'TabsList';

const TabsTrigger = React.forwardRef<HTMLButtonElement, TabsTriggerProps>(
  ({ className, value, ...props }, ref) => {
    const tabs = useTabsContext();

    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium',
          'ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-cyan)]',
          'disabled:pointer-events-none disabled:opacity-50',
          tabs.value === value
            ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-sm'
            : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
          className
        )}
        onClick={() => tabs.setValue(value)}
        {...props}
      />
    );
  }
);
TabsTrigger.displayName = 'TabsTrigger';

const TabsContent = React.forwardRef<HTMLDivElement, TabsContentProps>(
  ({ className, value, ...props }, ref) => {
    const tabs = useTabsContext();

    if (tabs.value !== value) {
      return null;
    }

    return (
      <div
        ref={ref}
        className={cn(
          'mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-cyan)]',
          className
        )}
        {...props}
      />
    );
  }
);
TabsContent.displayName = 'TabsContent';

export { Tabs, TabsList, TabsTrigger, TabsContent };
