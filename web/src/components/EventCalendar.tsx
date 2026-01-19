"use client";

import { Calendar } from "@/components/ui/calendar";
import { Event } from "@/types/event";
import { useMemo } from "react";

interface EventCalendarProps {
  events: Event[];
  selectedDate: Date | undefined;
  onSelectDate: (date: Date | undefined) => void;
}

export function EventCalendar({
  events,
  selectedDate,
  onSelectDate,
}: EventCalendarProps) {
  const eventDates = useMemo(() => {
    const dates = new Set<string>();
    events.forEach((event) => {
      const date = new Date(event.date);
      dates.add(date.toDateString());
    });
    return dates;
  }, [events]);

  const modifiers = useMemo(() => {
    return {
      hasEvent: (date: Date) => eventDates.has(date.toDateString()),
    };
  }, [eventDates]);

  return (
    <div className="flex justify-center">
      <Calendar
        mode="single"
        selected={selectedDate}
        onSelect={onSelectDate}
        modifiers={modifiers}
        modifiersClassNames={{
          hasEvent: "relative after:absolute after:bottom-1 after:left-1/2 after:-translate-x-1/2 after:w-1.5 after:h-1.5 after:bg-[#0EA5E9] after:rounded-full",
        }}
        className="!rounded-base"
      />
    </div>
  );
}
