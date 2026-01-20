"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { EventCalendar } from "@/components/EventCalendar";
import { EventList } from "@/components/EventList";
import { Event } from "@/types/event";

export default function Home() {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchEvents() {
      try {
        const res = await fetch("/api/events");
        const data = await res.json();
        setEvents(data);
      } catch (error) {
        console.error("Failed to fetch events:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchEvents();
  }, []);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      
      <main className="flex-1 w-full">
        <div className="max-w-4xl mx-auto px-4 py-6">
        {loading ? (
          <div className="text-center py-8">Se încarcă evenimentele...</div>
        ) : (
          <>
            <EventCalendar
              events={events}
              selectedDate={selectedDate}
              onSelectDate={setSelectedDate}
            />
            
            <EventList events={events} selectedDate={selectedDate} />
          </>
        )}
        </div>
      </main>
      
      <Footer />
    </div>
  );
}
