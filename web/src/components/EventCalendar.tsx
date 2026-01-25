"use client";

import { Calendar } from "@/components/ui/calendar";
import { Event } from "@/types/event";
import { ro } from "date-fns/locale";
import { useMemo, useState, useEffect } from "react";

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

  const [displayMonth, setDisplayMonth] = useState<Date>(selectedDate || new Date());

  useEffect(() => {
    if (selectedDate) {
      setDisplayMonth(selectedDate);
    }
  }, [selectedDate]);

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
    <div className="flex flex-col items-center gap-3">
      <Calendar
        mode="single"
        selected={selectedDate}
        onSelect={onSelectDate}
        month={displayMonth}
        onMonthChange={setDisplayMonth}
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
      <div 
        className="flex items-center gap-4 text-xs text-foreground/70"
        role="img"
        aria-label="Legendă: culorile indică numărul de evenimente - portocaliu deschis: 1-3, portocaliu mediu: 4-7, portocaliu închis: 8-12, portocaliu intens: peste 12 evenimente"
      >
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 bg-orange-200 border border-border rounded-sm" aria-hidden="true" />
          <span>1-3</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 bg-orange-400 border border-border rounded-sm" aria-hidden="true" />
          <span>4-7</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 bg-orange-500 border border-border rounded-sm" aria-hidden="true" />
          <span>8-12</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 bg-orange-600 border border-border rounded-sm" aria-hidden="true" />
          <span>12+</span>
        </span>
      </div>
    </div>
  );
}
