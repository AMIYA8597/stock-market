export default function LoadingCryptoPage(): JSX.Element {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={`crypto-load-${i}`} className="h-28 animate-pulse rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)]" />
      ))}
    </div>
  );
}
