"use client";

import { Calendar } from "@/components/ui/calendar";
import { Event } from "@/types/event";
import { ro } from "date-fns/locale";
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
  const firstOfMonth = useMemo(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  }, []);

  const eventCountByDate = useMemo(() => {
    const counts = new Map<string, number>();
    events.forEach((event) => {
      const dateKey = new Date(event.date).toDateString();
      counts.set(dateKey, (counts.get(dateKey) || 0) + 1);
    });
    return counts;
  }, [events]);

  const modifiers = useMemo(() => {
    return {
      heatLow: (date: Date) => {
        const count = eventCountByDate.get(date.toDateString()) || 0;
        return count >= 1 && count <= 3;
      },
      heatMedium: (date: Date) => {
        const count = eventCountByDate.get(date.toDateString()) || 0;
        return count >= 4 && count <= 7;
      },
      heatHigh: (date: Date) => {
        const count = eventCountByDate.get(date.toDateString()) || 0;
        return count >= 8 && count <= 12;
      },
      heatMax: (date: Date) => {
        const count = eventCountByDate.get(date.toDateString()) || 0;
        return count > 12;
      },
    };
  }, [eventCountByDate]);

  return (
    <div className="flex justify-center">
      <Calendar
        mode="single"
        selected={selectedDate}
        onSelect={onSelectDate}
        weekStartsOn={1}
        locale={ro}
        disabled={{ before: firstOfMonth }}
        fromMonth={firstOfMonth}
        modifiers={modifiers}
        modifiersClassNames={{
          heatLow: "!bg-orange-200 !text-orange-900 hover:!bg-orange-300",
          heatMedium: "!bg-orange-400 !text-white hover:!bg-orange-500",
          heatHigh: "!bg-orange-500 !text-white hover:!bg-orange-600",
          heatMax: "!bg-orange-600 !text-white hover:!bg-orange-700",
        }}
        className="!rounded-base"
      />
    </div>
  );
}
