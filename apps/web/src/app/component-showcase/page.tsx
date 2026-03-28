'use client';

import React, { useState } from 'react';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { DataTable, type Column } from '../../components/ui/DataTable';
import { RangeSlider } from '../../components/ui/RangeSlider';
import { Tooltip } from '../../components/ui/Tooltip';
import { Skeleton } from '../../components/ui/Skeleton';

interface Person {
  id: string;
  name: string;
  role: string;
  status: 'active' | 'inactive';
  profit: number;
}

const mockData: Person[] = [
  { id: '1', name: 'Alice Johnson', role: 'Analyst', status: 'active', profit: 2500.50 },
  { id: '2', name: 'Bob Smith', role: 'Trader', status: 'active', profit: 3200.75 },
  { id: '3', name: 'Carol White', role: 'Manager', status: 'inactive', profit: -450.25 },
];

export default function ComponentShowcasePage() {
  const [rangeValue, setRangeValue] = useState<[number, number]>([20, 80]);
  const [sortBy, setSortBy] = useState<string>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  const handleRangeChange = (value: number | [number, number]) => {
    if (Array.isArray(value)) {
      setRangeValue(value);
    }
  };

  const columns: Column<Person>[] = [
    {
      key: 'name',
      label: 'Name',
      render: (_, row) => <strong>{row.name}</strong>,
      sortable: true,
    },
    { key: 'role', label: 'Role', sortable: true },
    {
      key: 'status',
      label: 'Status',
      render: (value) => (
        <Badge variant={value === 'active' ? 'buy' : 'sell'}>
          {value === 'active' ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'profit',
      label: 'P&L',
      align: 'right',
      render: (value) => {
        const profit = typeof value === 'number' ? value : 0;
        return (
          <span className={profit > 0 ? 'text-[var(--accent-green)]' : 'text-[var(--accent-red)]'}>
            {profit > 0 ? '+' : ''}₹{profit.toFixed(2)}
          </span>
        );
      },
    },
  ];

  return (
    <main className="min-h-screen bg-[var(--bg-base)] py-12">
      <div className="container mx-auto px-4 max-w-6xl">
        <h1 className="text-4xl font-bold text-[var(--text-primary)] mb-2">UI Component Showcase</h1>
        <p className="text-[var(--text-secondary)] mb-12">
          Complete design system documentation and interactive component examples
        </p>

        {/* Buttons */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Buttons</CardTitle>
            <CardDescription>All button variants and sizes</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <p className="text-sm font-medium text-[var(--text-secondary)]">Default Variants</p>
              <div className="flex flex-wrap gap-3">
                <Button variant="default">Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="buy">Buy</Button>
                <Button variant="sell">Sell</Button>
                <Button variant="neutral">Neutral</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="destructive">Destructive</Button>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium text-[var(--text-secondary)]">Sizes</p>
              <div className="flex flex-wrap gap-3 items-center">
                <Button size="sm">Small</Button>
                <Button size="default">Default</Button>
                <Button size="lg">Large</Button>
                <Button size="xl">Extra Large</Button>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium text-[var(--text-secondary)]">States</p>
              <div className="flex flex-wrap gap-3">
                <Button disabled>Disabled</Button>
                <Button isLoading>Loading</Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Badges */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Badges</CardTitle>
            <CardDescription>Signal and status indicators</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <p className="text-sm font-medium text-[var(--text-secondary)]">Trade Signals</p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="buy">STRONG_BUY</Badge>
                  <Badge variant="buy">BUY</Badge>
                  <Badge variant="neutral">NEUTRAL</Badge>
                  <Badge variant="sell">SELL</Badge>
                  <Badge variant="sell">STRONG_SELL</Badge>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium text-[var(--text-secondary)]">Market Regimes</p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="bull">BULL</Badge>
                  <Badge variant="bear">BEAR</Badge>
                  <Badge variant="sideways">SIDEWAYS</Badge>
                  <Badge variant="crisis">CRISIS</Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Cards */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Cards</CardTitle>
            <CardDescription>Card component with all sections</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {['Card 1', 'Card 2', 'Card 3'].map((title) => (
                <Card key={title}>
                  <CardHeader>
                    <CardTitle className="text-lg">{title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-[var(--text-secondary)]">
                      This is a sample card with content and footer.
                    </p>
                  </CardContent>
                  <CardFooter>
                    <Button size="sm" variant="outline">Action</Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Forms */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Form Elements</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-[var(--text-primary)]">Input</label>
              <Input placeholder="Enter text..." />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-[var(--text-primary)]">Select</label>
              <Select>
                <option>Option 1</option>
                <option>Option 2</option>
                <option>Option 3</option>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-[var(--text-primary)]">Range Slider (20-80)</label>
              <RangeSlider min={0} max={100} step={5} value={rangeValue} onChange={handleRangeChange} />
              <div className="text-xs text-[var(--text-secondary)]">
                Selected: {rangeValue[0]} - {rangeValue[1]}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Tabs (Three Section Layout)</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="tab1">
              <TabsList>
                <TabsTrigger value="tab1">Tab 1: Watchlist</TabsTrigger>
                <TabsTrigger value="tab2">Tab 2: Signals</TabsTrigger>
                <TabsTrigger value="tab3">Tab 3: News</TabsTrigger>
              </TabsList>
              <TabsContent value="tab1" className="p-4 bg-[var(--bg-elevated)] rounded">
                <p className="text-[var(--text-secondary)]">Watchlist content goes here</p>
              </TabsContent>
              <TabsContent value="tab2" className="p-4 bg-[var(--bg-elevated)] rounded">
                <p className="text-[var(--text-secondary)]">Signals content goes here</p>
              </TabsContent>
              <TabsContent value="tab3" className="p-4 bg-[var(--bg-elevated)] rounded">
                <p className="text-[var(--text-secondary)]">News content goes here</p>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Data Table */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Data Table</CardTitle>
            <CardDescription>Sortable table with custom rendering</CardDescription>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={columns}
              data={mockData}
              rowKey="id"
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={(key) => {
                if (sortBy === key) {
                  setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                } else {
                  setSortBy(key);
                  setSortOrder('asc');
                }
              }}
            />
          </CardContent>
        </Card>

        {/* Loading States */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Loading States</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-medium text-[var(--text-secondary)]">Skeleton Loaders</p>
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-8 w-2/3" />
              <Skeleton className="h-8 w-1/2" />
            </div>
          </CardContent>
        </Card>

        {/* Tooltips */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Tooltips</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <Tooltip content="Top tooltip">
                <Button variant="outline">Top</Button>
              </Tooltip>
              <Tooltip content="Right tooltip" side="right">
                <Button variant="outline">Right</Button>
              </Tooltip>
              <Tooltip content="Bottom tooltip" side="bottom">
                <Button variant="outline">Bottom</Button>
              </Tooltip>
              <Tooltip content="Left tooltip" side="left">
                <Button variant="outline">Left</Button>
              </Tooltip>
            </div>
          </CardContent>
        </Card>

        {/* Color System */}
        <Card>
          <CardHeader>
            <CardTitle>Color System</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { name: 'bg-base', color: 'var(--bg-base)' },
                { name: 'bg-surface', color: 'var(--bg-surface)' },
                { name: 'bg-elevated', color: 'var(--bg-elevated)' },
                { name: 'accent-cyan', color: 'var(--accent-cyan)' },
                { name: 'accent-green', color: 'var(--accent-green)' },
                { name: 'accent-red', color: 'var(--accent-red)' },
                { name: 'accent-amber', color: 'var(--accent-amber)' },
                { name: 'accent-purple', color: 'var(--accent-purple)' },
              ].map((item) => (
                <div key={item.name} className="space-y-2">
                  <div className="h-20 rounded border border-[var(--border-subtle)]" style={{ backgroundColor: item.color }} />
                  <p className="text-xs font-medium text-[var(--text-primary)]">{item.name}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
