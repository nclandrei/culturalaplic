import { Suspense } from "react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { EventsView } from "@/components/EventsView";
import { Event, Category } from "@/types/event";
import { promises as fs } from "fs";
import path from "path";

interface RawEvent {
  title: string;
  artist: string | null;
  venue: string;
  date: string;
  url: string;
  source: string;
  category: Category;
  price: string | null;
  spotify_url: string | null;
  description?: string | null;
  description_source?: "scraped" | "ai" | null;
  image_url?: string | null;
  video_url?: string | null;
}

interface EventsData {
  music_events?: RawEvent[];
  theatre_events?: RawEvent[];
  culture_events?: RawEvent[];
}

async function getEvents(): Promise<Event[]> {
  const eventsPath = path.join(process.cwd(), "public", "data", "events.json");
  
  try {
    const fileContent = await fs.readFile(eventsPath, "utf-8");
    const eventsData: EventsData = JSON.parse(fileContent);
    
    const rawEvents = [
      ...(eventsData.music_events || []),
      ...(eventsData.theatre_events || []),
      ...(eventsData.culture_events || []),
    ];

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    let allEvents: Event[] = rawEvents.map((e) => ({
      title: e.title,
      artist: e.artist,
      venue: e.venue,
      date: e.date,
      url: e.url,
      source: e.source,
      category: e.category,
      price: e.price,
      spotifyUrl: e.spotify_url,
      spotifyMatch: !!e.spotify_url,
      description: e.description,
      descriptionSource: e.description_source,
      imageUrl: e.image_url,
      videoUrl: e.video_url,
    }));

    allEvents = allEvents.filter((event) => new Date(event.date) >= today);
    allEvents.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    return allEvents;
  } catch {
    return [];
  }
}

export default async function Home() {
  const events = await getEvents();

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      
      <main id="main-content" className="flex-1 w-full" aria-label="Evenimente culturale">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <Suspense fallback={null}>
            <EventsView events={events} />
          </Suspense>
        </div>
      </main>
      
      <Footer />
    </div>
  );
}
