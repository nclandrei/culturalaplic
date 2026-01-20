import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import type { Event, Category } from "@/types/event";

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
}

interface EventsData {
  music_events?: RawEvent[];
  theatre_events?: RawEvent[];
  culture_events?: RawEvent[];
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const category = searchParams.get("category") as Category | null;
  const from = searchParams.get("from");
  const to = searchParams.get("to");
  const limit = searchParams.get("limit");

  const fromDate = from ? new Date(from) : new Date();
  fromDate.setHours(0, 0, 0, 0);

  const toDate = to ? new Date(to) : null;
  if (toDate) {
    toDate.setHours(23, 59, 59, 999);
  }

  const maxResults = limit ? parseInt(limit, 10) : null;

  try {
    const eventsPath = path.join(process.cwd(), "public", "data", "events.json");
    let eventsData: EventsData = {};

    try {
      const fileContent = await fs.readFile(eventsPath, "utf-8");
      eventsData = JSON.parse(fileContent);
    } catch {
      return NextResponse.json([]);
    }

    const rawEvents = [
      ...(eventsData.music_events || []),
      ...(eventsData.theatre_events || []),
      ...(eventsData.culture_events || []),
    ];

    // Transform snake_case from Python to camelCase for frontend
    let allEvents: Event[] = rawEvents.map((e) => ({
      title: e.title as string,
      artist: e.artist as string | null,
      venue: e.venue as string,
      date: e.date as string,
      url: e.url as string,
      source: e.source as string,
      category: e.category as Category,
      price: e.price as string | null,
      spotifyUrl: e.spotify_url as string | null,
      spotifyMatch: !!e.spotify_url,
    }));

    if (category) {
      allEvents = allEvents.filter((event) => event.category === category);
    }

    allEvents = allEvents.filter((event) => {
      const eventDate = new Date(event.date);
      if (eventDate < fromDate) return false;
      if (toDate && eventDate > toDate) return false;
      return true;
    });

    allEvents.sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    if (maxResults && maxResults > 0) {
      allEvents = allEvents.slice(0, maxResults);
    }

    return NextResponse.json(allEvents);
  } catch (error) {
    console.error("Error reading events:", error);
    return NextResponse.json(
      { error: "Failed to fetch events" },
      { status: 500 }
    );
  }
}
