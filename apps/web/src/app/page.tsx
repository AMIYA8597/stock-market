import TickerStrip from '@/components/dashboard/TickerStrip';
import Heatmap from '@/components/dashboard/Heatmap';
import AISummaryPanel from '@/components/dashboard/AISummaryPanel';

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-heading text-primary mb-4">
          NeuroQuant
        </h1>
        <p className="text-text-secondary mb-8">
          AI-Powered Stock Market Platform
        </p>

        {/* Ticker Strip */}
        <TickerStrip />

        {/* Heatmap and AI Summary Panel */}
        <div className="grid grid-cols-12 gap-4 mt-8">
          <div className="col-span-7">
            <Heatmap />
          </div>
          <div className="col-span-5">
            <AISummaryPanel />
          </div>
        </div>
      </div>
    </main>
  );
}