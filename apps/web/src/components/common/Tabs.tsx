'use client';

import { ReactNode, useState } from 'react';

/**
 * Tabs Component
 * 
 * Reusable tab navigation component with:
 * - Active/inactive states
 * - Icon support
 * - Smooth transitions
 * - Customizable content
 */

interface TabItem {
  id: string;
  label: string;
  icon?: string;
  content: ReactNode;
}

interface TabsProps {
  items: TabItem[];
  defaultTabId?: string;
  onTabChange?: (tabId: string) => void;
}

const Tabs = ({
  items,
  defaultTabId,
  onTabChange,
}: TabsProps): JSX.Element => {
  const [activeTab, setActiveTab] = useState(defaultTabId || items[0]?.id || '');

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    onTabChange?.(tabId);
  };

  const activeTabItem = items.find((item) => item.id === activeTab);

  return (
    <div className="w-full">
      {/* Tab navigation */}
      <div className="flex gap-2 border-b border-[#1E2532] overflow-x-auto">
        {items.map((item) => {
          const isActive = item.id === activeTab;

          return (
            <button
              key={item.id}
              onClick={() => handleTabChange(item.id)}
              className={`px-4 py-3 font-semibold text-sm whitespace-nowrap transition-all border-b-2 flex items-center gap-2 ${
                isActive
                  ? 'text-[#00D4FF] border-[#00D4FF]'
                  : 'text-[#8B9BB4] border-transparent hover:text-[#E8EAED] hover:border-[#1E2532]'
              }`}
            >
              {item.icon && <span className="text-base">{item.icon}</span>}
              {item.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="pt-6 animate-fade-in">
        {activeTabItem && activeTabItem.content}
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        .animate-fade-in {
          animation: fadeIn 0.2s ease-in;
        }
      `}</style>
    </div>
  );
};

export default Tabs;
