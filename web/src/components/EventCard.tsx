"use client";

import { useState, useEffect } from "react";
import { Event, Category } from "@/types/event";
import { EventDetailModal, hasEnrichmentData } from "./EventDetailModal";
import { generateEventId } from "@/lib/eventId";

const categoryColors: Record<Category, string> = {
  music: "bg-[#0EA5E9]",
  theatre: "bg-[#EC4899]",
  culture: "bg-[#EAB308]",
};

const categoryLabels: Record<Category, string> = {
  music: "Muzică",
  theatre: "Teatru",
  culture: "Cultură",
};

interface EventCardProps {
  event: Event;
  isInitiallyOpen?: boolean;
  onModalOpened?: () => void;
}

export function EventCard({ event, isInitiallyOpen, onModalOpened }: EventCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    if (isInitiallyOpen) {
      setIsModalOpen(true);
      onModalOpened?.();
    }
  }, [isInitiallyOpen, onModalOpened]);

  const updateUrlWithEventId = (open: boolean) => {
    const url = new URL(window.location.href);
    if (open) {
      const eventDate = new Date(event.date);
      url.searchParams.set("year", eventDate.getFullYear().toString());
      url.searchParams.set("month", (eventDate.getMonth() + 1).toString());
      url.searchParams.set("day", eventDate.getDate().toString());
      url.searchParams.set("eventId", generateEventId(event));
    } else {
      url.searchParams.delete("eventId");
    }
    window.history.replaceState({}, "", url.toString());
  };

  const handleOpenModal = () => {
    setIsModalOpen(true);
    updateUrlWithEventId(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    updateUrlWithEventId(false);
  };
  
  const showDetaliiButton =
    (event.category === "theatre" || event.category === "culture") &&
    hasEnrichmentData(event);
  const eventDate = new Date(event.date);
  const hasTime = eventDate.getHours() !== 0 || eventDate.getMinutes() !== 0;
  const timeString = hasTime
    ? eventDate.toLocaleTimeString("ro-RO", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  const handleCardClick = (e: React.MouseEvent | React.KeyboardEvent) => {
    if ((e.target as HTMLElement).closest('a, button')) return;
    window.open(event.url, '_blank', 'noopener,noreferrer');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleCardClick(e);
    }
  };

  return (
    <article
      onClick={handleCardClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="link"
      aria-label={`${event.title}${event.artist ? `, ${event.artist}` : ''} la ${event.venue}${timeString ? ` la ora ${timeString}` : ''}${event.price ? `, ${event.price}` : ''}`}
      className="cursor-pointer block rounded-base border-2 border-border bg-secondary-background p-4 shadow-shadow transition-all hover:translate-x-[4px] hover:translate-y-[4px] hover:shadow-none focus:outline-none focus:ring-2 focus:ring-border focus:ring-offset-2"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`${categoryColors[event.category]} px-2 py-0.5 text-xs font-bold text-white rounded-base border-2 border-border`}
            >
              {categoryLabels[event.category]}
            </span>
            {event.spotifyMatch && event.spotifyUrl && (
              <a
                href={event.spotifyUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-1 text-xs text-[#1DB954] font-bold hover:underline focus:outline-none focus:ring-2 focus:ring-[#1DB954] focus:ring-offset-1 rounded"
                aria-label={`Ascultă ${event.artist || event.title} pe Spotify`}
              >
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
                </svg>
                Ascultă
              </a>
            )}
            {showDetaliiButton && (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleOpenModal();
                }}
                className="flex items-center gap-1 text-xs text-[#EC4899] font-bold hover:underline focus:outline-none focus:ring-2 focus:ring-[#EC4899] focus:ring-offset-1 rounded"
                aria-label={`Vezi detalii pentru ${event.title}`}
              >
                <svg
                  className="w-4 h-4 shrink-0"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 16v-4" />
                  <circle cx="12" cy="8" r="0.5" fill="currentColor" />
                </svg>
                Detalii
              </button>
            )}
          </div>
          
          <h3 className="font-bold text-lg leading-tight mb-1 truncate">
            {event.title}
          </h3>
          
          {event.artist && (
            <p className="text-sm text-foreground/70 mb-1 truncate">
              {event.artist}
            </p>
          )}
          
          <p className="text-sm font-medium">
            {event.venue}{timeString && ` • ${timeString}`}
          </p>
        </div>
        
        <div className="text-right shrink-0">
          {event.price && (
            <span className="inline-block bg-main px-2 py-1 text-sm font-bold rounded-base border-2 border-border">
              {event.price}
            </span>
          )}
        </div>
      </div>
      
      <EventDetailModal
        event={event}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
      />
    </article>
  );
}
