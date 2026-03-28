import React from 'react';
import * as RadixAvatar from '@radix-ui/react-avatar';
import { cn } from '@/lib/utils';

interface AvatarProps {
  src?: string;
  alt?: string;
  fallback?: string;
  className?: string;
}

export function Avatar({ src, alt = 'User avatar', fallback = 'U', className }: AvatarProps): JSX.Element {
  return (
    <RadixAvatar.Root
      className={cn(
        'relative inline-flex h-9 w-9 shrink-0 overflow-hidden rounded-full border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)]',
        className
      )}
    >
      {src ? <RadixAvatar.Image src={src} alt={alt} className="h-full w-full object-cover" /> : null}
      <RadixAvatar.Fallback className="flex h-full w-full items-center justify-center text-xs font-semibold text-[var(--ds-text-secondary)]">
        {fallback}
      </RadixAvatar.Fallback>
    </RadixAvatar.Root>
  );
}
