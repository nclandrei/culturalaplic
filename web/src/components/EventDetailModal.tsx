"use client";

import { Event } from "@/types/event";
import { Component, ReactNode, useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { generateEventId } from "@/lib/eventId";

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

type ShareStatus = "idle" | "copied" | "error";

function ModalContent({ event, onClose }: Omit<EventDetailModalProps, "isOpen">) {
  const [imageError, setImageError] = useState(false);
  const [shareStatus, setShareStatus] = useState<ShareStatus>("idle");
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);
  const eventDate = new Date(event.date);

  const generateShareUrl = useCallback(() => {
    const eventId = generateEventId(event);
    const params = new URLSearchParams();
    params.set("year", eventDate.getFullYear().toString());
    params.set("month", (eventDate.getMonth() + 1).toString());
    params.set("day", eventDate.getDate().toString());
    params.set("eventId", eventId);
    return `${window.location.origin}${window.location.pathname}?${params.toString()}`;
  }, [event, eventDate]);

  const handleShare = useCallback(async () => {
    const shareUrl = generateShareUrl();
    const shareData = {
      title: event.title,
      text: `${event.title} - ${event.venue}`,
      url: shareUrl,
    };

    if (navigator.share && navigator.canShare?.(shareData)) {
      try {
        await navigator.share(shareData);
        setShareStatus("idle");
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          try {
            await navigator.clipboard.writeText(shareUrl);
            setShareStatus("copied");
            setTimeout(() => setShareStatus("idle"), 2000);
          } catch {
            setShareStatus("error");
            setTimeout(() => setShareStatus("idle"), 2000);
          }
        }
      }
    } else {
      try {
        await navigator.clipboard.writeText(shareUrl);
        setShareStatus("copied");
        setTimeout(() => setShareStatus("idle"), 2000);
      } catch {
        setShareStatus("error");
        setTimeout(() => setShareStatus("idle"), 2000);
      }
    }
  }, [generateShareUrl, event.title, event.venue]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
      return;
    }

    if (e.key === 'Tab') {
      const focusableElements = modalRef.current?.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (!focusableElements || focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    }
  }, [onClose]);

  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement;
    document.addEventListener('keydown', handleKeyDown);
    
    const closeButton = modalRef.current?.querySelector<HTMLButtonElement>('button[aria-label="Închide"]');
    closeButton?.focus();

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previousActiveElement.current?.focus();
    };
  }, [handleKeyDown]);
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

  const modalId = `modal-title-${event.title.replace(/\s+/g, '-').toLowerCase()}`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={onClose}
      role="presentation"
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={modalId}
        className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-secondary-background border-4 border-border rounded-base shadow-shadow"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Action buttons */}
        <div className="absolute top-3 right-3 z-10 flex gap-2">
          {/* Share button */}
          <button
            onClick={handleShare}
            className="w-8 h-8 flex items-center justify-center bg-main border-2 border-border rounded-base hover:bg-main/80 transition-colors"
            aria-label="Distribuie"
          >
            {shareStatus === "idle" && (
              <svg
                className="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="18" cy="5" r="3" />
                <circle cx="6" cy="12" r="3" />
                <circle cx="18" cy="19" r="3" />
                <path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" />
              </svg>
            )}
            {shareStatus === "copied" && (
              <svg
                className="w-4 h-4 text-green-600"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M20 6L9 17l-5-5" />
              </svg>
            )}
            {shareStatus === "error" && (
              <svg
                className="w-4 h-4 text-red-600"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            )}
          </button>

          {/* Close button */}
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center bg-main border-2 border-border rounded-base hover:bg-main/80 transition-colors"
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
              aria-hidden="true"
            >
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Image/Video section */}
        {event.videoUrl ? (
          <div className="w-full aspect-video">
            <iframe
              src={event.videoUrl}
              className="w-full h-full border-b-4 border-border"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              title={`Video pentru ${event.title}`}
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
            <span aria-hidden="true">📍</span> {event.venue}
          </p>

          {/* Title */}
          <h2 id={modalId} className="text-xl font-bold mb-3">{event.title}</h2>

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
