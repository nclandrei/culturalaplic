"use client";

import { Event } from "@/types/event";
import { Component, ReactNode, useState } from "react";
import { createPortal } from "react-dom";

const categoryColors: Record<string, string> = {
  music: "bg-[#0EA5E9]",
  theatre: "bg-[#EC4899]",
  culture: "bg-[#EAB308]",
};

const categoryLabels: Record<string, string> = {
  music: "Muzică",
  theatre: "Teatru",
  culture: "Cultură",
};

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || null;
    }
    return this.props.children;
  }
}

interface EventDetailModalProps {
  event: Event;
  isOpen: boolean;
  onClose: () => void;
}

function ModalContent({ event, onClose }: Omit<EventDetailModalProps, "isOpen">) {
  const [imageError, setImageError] = useState(false);
  const eventDate = new Date(event.date);
  const dateString = eventDate.toLocaleDateString("ro-RO", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const hasTime = eventDate.getHours() !== 0 || eventDate.getMinutes() !== 0;
  const timeString = hasTime
    ? eventDate.toLocaleTimeString("ro-RO", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  const hasDescription = !!event.description;
  const isAiGenerated = event.descriptionSource === "ai";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-secondary-background border-4 border-border rounded-base shadow-shadow"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 z-10 w-8 h-8 flex items-center justify-center bg-main border-2 border-border rounded-base hover:bg-main/80 transition-colors"
          aria-label="Închide"
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        {/* Image/Video section */}
        {event.videoUrl ? (
          <div className="w-full aspect-video">
            <iframe
              src={event.videoUrl}
              className="w-full h-full border-b-4 border-border"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        ) : event.imageUrl && !imageError ? (
          <div className="w-full">
            <img
              src={event.imageUrl}
              alt={event.title}
              className="w-full h-auto max-h-64 object-cover border-b-4 border-border"
              onError={() => setImageError(true)}
            />
          </div>
        ) : null}

        {/* Content */}
        <div className="p-5">
          {/* Category + Date + Venue */}
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span
              className={`${categoryColors[event.category]} px-2 py-0.5 text-xs font-bold text-white rounded-base border-2 border-border`}
            >
              {categoryLabels[event.category]}
            </span>
            <span className="text-sm text-foreground/70">
              {dateString}
              {timeString && ` • ${timeString}`}
            </span>
          </div>
          <p className="text-sm font-medium text-foreground/80 mb-2">
            📍 {event.venue}
          </p>

          {/* Title */}
          <h2 className="text-xl font-bold mb-3">{event.title}</h2>

          {/* Artist if present */}
          {event.artist && (
            <p className="text-foreground/70 mb-3">{event.artist}</p>
          )}

          {/* Description */}
          <div className="mb-4">
            {hasDescription ? (
              <>
                {isAiGenerated && (
                  <span className="inline-block mb-2 px-2 py-0.5 text-xs font-bold bg-purple-200 text-purple-800 rounded-base border-2 border-border">
                    ✨ Rezumat
                  </span>
                )}
                <p className="text-foreground/90 leading-relaxed whitespace-pre-line">
                  {event.description}
                </p>
              </>
            ) : (
              <p className="text-foreground/70 italic">
                <a
                  href={event.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-foreground"
                >
                  Vizitează pagina pentru detalii →
                </a>
              </p>
            )}
          </div>

          {/* Price + CTA */}
          <div className="flex items-center justify-between gap-3 pt-3 border-t-2 border-border">
            {event.price && (
              <span className="inline-block bg-main px-3 py-1 text-sm font-bold rounded-base border-2 border-border">
                {event.price}
              </span>
            )}
            <a
              href={event.url}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-auto inline-block bg-main px-4 py-2 font-bold rounded-base border-2 border-border shadow-shadow hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
            >
              Cumpără Bilete
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

export function EventDetailModal({ event, isOpen, onClose }: EventDetailModalProps) {
  if (!isOpen || typeof document === "undefined") return null;

  return createPortal(
    <ErrorBoundary fallback={null}>
      <ModalContent event={event} onClose={onClose} />
    </ErrorBoundary>,
    document.body
  );
}

export function hasEnrichmentData(event: Event): boolean {
  return !!(event.description || event.imageUrl || event.videoUrl);
}
