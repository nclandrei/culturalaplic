"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { EventCalendar } from "@/components/EventCalendar";
import { EventList } from "@/components/EventList";
import { EventListSkeleton } from "@/components/EventCardSkeleton";
import { Event } from "@/types/event";
import { Skeleton } from "@/components/ui/skeleton";
import { findEventById } from "@/lib/eventId";

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
  const [initialOpenEventId, setInitialOpenEventId] = useState<string | null>(null);
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const year = searchParams.get("year");
    const month = searchParams.get("month");
    const day = searchParams.get("day");
    const eventId = searchParams.get("eventId");

    if (year && month && day) {
      const dateFromUrl = new Date(
        parseInt(year, 10),
        parseInt(month, 10) - 1,
        parseInt(day, 10)
      );
      if (!isNaN(dateFromUrl.getTime())) {
        setSelectedDate(dateFromUrl);
        if (eventId) {
          const foundEvent = findEventById(events, eventId);
          if (foundEvent) {
            setInitialOpenEventId(eventId);
          }
        }
        setIsHydrated(true);
        return;
      }
    }
    setSelectedDate(new Date());
    setIsHydrated(true);
  }, [searchParams, events]);

  const handleEventModalOpened = useCallback(() => {
    setInitialOpenEventId(null);
  }, []);

  const handleSelectDate = useCallback(
    (date: Date | undefined) => {
      setSelectedDate(date);
      if (date) {
        const params = new URLSearchParams();
        params.set("year", date.getFullYear().toString());
        params.set("month", (date.getMonth() + 1).toString());
        params.set("day", date.getDate().toString());
        router.replace(`?${params.toString()}`, { scroll: false });
      }
    },
    [router]
  );

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
        onSelectDate={handleSelectDate}
      />
      <EventList
        events={events}
        selectedDate={selectedDate}
        initialOpenEventId={initialOpenEventId}
        onEventModalOpened={handleEventModalOpened}
      />
    </>
  );
}
