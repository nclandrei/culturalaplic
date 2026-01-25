"use client";

import { Event, Category } from "@/types/event";
import { EventCard } from "./EventCard";
import { Button } from "./ui/button";
import { useMemo, useState } from "react";

type CategoryFilter = Category | "all";

const CATEGORY_CONFIG: Record<CategoryFilter, { label: string; emoji: string }> = {
  all: { label: "Toate", emoji: "📅" },
  music: { label: "Muzică", emoji: "🎵" },
  theatre: { label: "Teatru", emoji: "🎭" },
  culture: { label: "Cultură", emoji: "🎨" },
};

interface EventListProps {
  events: Event[];
  selectedDate: Date | undefined;
}

export function EventList({ events, selectedDate }: EventListProps) {
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");

  const eventsForDate = useMemo(() => {
    if (!selectedDate) return [];
    
    return events.filter((event) => {
      const eventDate = new Date(event.date);
      return eventDate.toDateString() === selectedDate.toDateString();
    });
  }, [events, selectedDate]);

  const filteredEvents = useMemo(() => {
    if (categoryFilter === "all") return eventsForDate;
    return eventsForDate.filter((event) => event.category === categoryFilter);
  }, [eventsForDate, categoryFilter]);

  const categoryCounts = useMemo(() => {
    const counts: Record<CategoryFilter, number> = {
      all: eventsForDate.length,
      music: 0,
      theatre: 0,
      culture: 0,
    };
    eventsForDate.forEach((event) => {
      counts[event.category]++;
    });
    return counts;
  }, [eventsForDate]);

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
      
      {eventsForDate.length > 0 && (
        <div 
          className="flex flex-wrap gap-2 mb-4"
          role="group"
          aria-label="Filtrează evenimente după categorie"
        >
          {(Object.keys(CATEGORY_CONFIG) as CategoryFilter[]).map((category) => {
            const { label, emoji } = CATEGORY_CONFIG[category];
            const count = categoryCounts[category];
            const isActive = categoryFilter === category;
            
            if (category !== "all" && count === 0) return null;
            
            return (
              <Button
                key={category}
                onClick={() => setCategoryFilter(category)}
                variant={isActive ? "reverse" : "neutral"}
                size="sm"
                className="gap-1.5"
                aria-pressed={isActive}
                aria-label={`${label} - ${count} ${count === 1 ? 'eveniment' : 'evenimente'}`}
              >
                <span aria-hidden="true">{emoji}</span>
                <span>{label}</span>
                <span 
                  className={`
                    px-1.5 py-0.5 text-xs rounded-base
                    ${isActive ? "bg-main-foreground/20" : "bg-foreground/10"}
                  `}
                  aria-hidden="true"
                >
                  {count}
                </span>
              </Button>
            );
          })}
        </div>
      )}

      <div aria-live="polite" aria-atomic="true">
        {filteredEvents.length === 0 ? (
          <div className="rounded-base border-2 border-border bg-secondary-background p-8 text-center shadow-shadow">
            <p className="text-foreground/70">
              {eventsForDate.length === 0
                ? "Nu sunt evenimente programate pentru această zi."
                : `Nu sunt evenimente de ${CATEGORY_CONFIG[categoryFilter].label.toLowerCase()} în această zi.`}
            </p>
          </div>
        ) : (
          <div 
            className="space-y-3"
            role="feed"
            aria-label={`${filteredEvents.length} ${filteredEvents.length === 1 ? 'eveniment' : 'evenimente'} pentru ${formattedDate}`}
          >
            {filteredEvents.map((event, index) => (
              <EventCard key={`${event.url}-${index}`} event={event} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
