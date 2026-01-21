import { Skeleton } from "@/components/ui/skeleton";

export function EventCardSkeleton() {
  return (
    <div className="rounded-base border-2 border-border bg-secondary-background p-4 shadow-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <Skeleton className="h-5 w-16" />
          </div>
          <Skeleton className="h-6 w-3/4 mb-1" />
          <Skeleton className="h-4 w-1/2 mb-1" />
          <Skeleton className="h-4 w-2/3" />
        </div>
        <Skeleton className="h-8 w-16 shrink-0" />
      </div>
    </div>
  );
}

export function EventListSkeleton() {
  return (
    <div className="mt-6">
      <Skeleton className="h-7 w-64 mb-4" />
      <div className="space-y-3">
        <EventCardSkeleton />
        <EventCardSkeleton />
        <EventCardSkeleton />
      </div>
    </div>
  );
}
