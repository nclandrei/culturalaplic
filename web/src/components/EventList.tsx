"use client";

import { Event } from "@/types/event";
import { EventCard } from "./EventCard";
import { useMemo } from "react";

interface EventListProps {
  events: Event[];
  selectedDate: Date | undefined;
}

export function EventList({ events, selectedDate }: EventListProps) {
  const filteredEvents = useMemo(() => {
    if (!selectedDate) return [];
    
    return events.filter((event) => {
      const eventDate = new Date(event.date);
      return eventDate.toDateString() === selectedDate.toDateString();
    });
  }, [events, selectedDate]);

  const formattedDate = selectedDate
    ? selectedDate.toLocaleDateString("ro-RO", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "";

  return (
    <div className="mt-6">
      <h2 className="text-xl font-bold mb-4 capitalize">{formattedDate}</h2>
      
      {filteredEvents.length === 0 ? (
        <div className="rounded-base border-2 border-border bg-secondary-background p-8 text-center shadow-shadow">
          <p className="text-foreground/70">
            Nu sunt evenimente programate pentru această zi.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEvents.map((event, index) => (
            <EventCard key={`${event.url}-${index}`} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}
