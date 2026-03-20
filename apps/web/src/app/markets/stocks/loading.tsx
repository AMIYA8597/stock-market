export default function LoadingStocksPage(): JSX.Element {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 9 }, (_, i) => (
        <div key={`stock-load-${i}`} className="h-28 animate-pulse rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)]" />
      ))}
    </div>
  );
}
