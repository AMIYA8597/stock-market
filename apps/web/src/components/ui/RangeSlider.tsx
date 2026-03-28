import React from 'react';
import { cn } from '../../lib/utils';

interface RangeSliderProps {
  min: number;
  max: number;
  step?: number;
  value: number | [number, number];
  onChange: (value: number | [number, number]) => void;
  className?: string;
}

const RangeSlider = React.forwardRef<HTMLDivElement, RangeSliderProps>(
  ({ min, max, step = 1, value, onChange, className, ...props }, ref) => {
    const isRange = Array.isArray(value);

    return (
      <div ref={ref} className={cn('w-full', className)}>
        {isRange ? (
          <div className="flex gap-4">
            <input
              type="range"
              min={min}
              max={max}
              step={step}
              value={value[0]}
              onChange={(e) => onChange([Number(e.currentTarget.value), value[1]])}
              className="w-full h-2 bg-[var(--bg-elevated)] rounded-lg appearance-none cursor-pointer accent-[var(--accent-cyan)]"
              {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
            />
            <input
              type="range"
              min={min}
              max={max}
              step={step}
              value={value[1]}
              onChange={(e) => onChange([value[0], Number(e.currentTarget.value)])}
              className="w-full h-2 bg-[var(--bg-elevated)] rounded-lg appearance-none cursor-pointer accent-[var(--accent-cyan)]"
              {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
            />
          </div>
        ) : (
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => onChange(Number(e.currentTarget.value))}
            className="w-full h-2 bg-[var(--bg-elevated)] rounded-lg appearance-none cursor-pointer accent-[var(--accent-cyan)]"
            {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
          />
        )}
      </div>
    );
  }
);
RangeSlider.displayName = 'RangeSlider';

export { RangeSlider };
