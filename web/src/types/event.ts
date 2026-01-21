export type Category = "music" | "theatre" | "culture";

export type DescriptionSource = "scraped" | "ai";

export interface Event {
  title: string;
  artist: string | null;
  venue: string;
  date: string; // ISO date string
  url: string;
  source: string;
  category: Category;
  price: string | null;
  spotifyMatch?: boolean;
  spotifyUrl?: string | null;
  // Enrichment fields for theatre/culture events
  description?: string | null;
  descriptionSource?: DescriptionSource | null;
  imageUrl?: string | null;
  videoUrl?: string | null;
}
