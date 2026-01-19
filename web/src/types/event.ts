export type Category = "music" | "theatre" | "culture";

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
}
