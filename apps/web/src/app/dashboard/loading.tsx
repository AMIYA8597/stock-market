import { Skeleton } from "@/components/ui/Skeleton";

export default function DashboardLoading(): JSX.Element {
  return (
    <div className="space-y-6 pb-8">
      <Skeleton className="h-[420px] rounded-[1.5rem]" />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-[152px] rounded-[1.5rem]" />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Skeleton className="h-[420px] rounded-[1.5rem]" />
        <Skeleton className="h-[420px] rounded-[1.5rem]" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Skeleton className="h-[360px] rounded-[1.5rem]" />
        <Skeleton className="h-[360px] rounded-[1.5rem]" />
      </div>
    </div>
  );
}