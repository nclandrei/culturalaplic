"use client";

import { useState, useEffect } from "react";
import { EventCalendar } from "@/components/EventCalendar";
import { EventList } from "@/components/EventList";
import { EventListSkeleton } from "@/components/EventCardSkeleton";
import { Event } from "@/types/event";
import { Skeleton } from "@/components/ui/skeleton";

interface EventsViewProps {
  events: Event[];
}

function CalendarSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-32" />
        <div className="flex gap-2">
          <Skeleton className="h-8 w-8" />
          <Skeleton className="h-8 w-8" />
        </div>
      </div>
      <div className="grid grid-cols-7 gap-1">
        {Array.from({ length: 7 }).map((_, i) => (
          <Skeleton key={`header-${i}`} className="h-8 w-full" />
        ))}
        {Array.from({ length: 35 }).map((_, i) => (
          <Skeleton key={`day-${i}`} className="h-10 w-full" />
        ))}
      </div>
    </div>
  );
}

export function EventsView({ events }: EventsViewProps) {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setSelectedDate(new Date());
    setIsHydrated(true);
  }, []);

  if (!isHydrated) {
    return (
      <>
        <CalendarSkeleton />
        <EventListSkeleton />
      </>
    );
  }

  return (
    <>
      <EventCalendar
        events={events}
        selectedDate={selectedDate}
        onSelectDate={setSelectedDate}
      />
      <EventList events={events} selectedDate={selectedDate} />
    </>
  );
}
