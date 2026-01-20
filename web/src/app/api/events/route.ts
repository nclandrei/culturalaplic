import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import type { Event, Category } from "@/types/event";

interface EventsData {
  music_events?: Event[];
  theatre_events?: Event[];
  culture_events?: Event[];
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
    const eventsPath = path.join(process.cwd(), "..", "data", "events.json");
    let eventsData: EventsData = {};

    try {
      const fileContent = await fs.readFile(eventsPath, "utf-8");
      eventsData = JSON.parse(fileContent);
    } catch {
      return NextResponse.json([]);
    }

    let allEvents: Event[] = [
      ...(eventsData.music_events || []),
      ...(eventsData.theatre_events || []),
      ...(eventsData.culture_events || []),
    ];

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
