import { Event } from "@/types/event";

/**
 * Generate a stable, URL-safe ID for an event.
 * Uses title + venue + normalized date timestamp for stability.
 * Avoids using URL which can have variations (www, trailing slashes, etc.)
 */
export function generateEventId(event: Event): string {
  const normalizedDate = new Date(event.date).getTime();
  const input = `${event.title}|${event.venue}|${normalizedDate}`;
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  // Convert to base36 for shorter URL-safe string
  return Math.abs(hash).toString(36);
}

/**
 * Find an event by its generated ID from a list of events.
 */
export function findEventById(events: Event[], id: string): Event | undefined {
  return events.find((event) => generateEventId(event) === id);
}
