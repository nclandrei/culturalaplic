"use client";

import { useState } from "react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { EventCalendar } from "@/components/EventCalendar";
import { EventList } from "@/components/EventList";
import { Event } from "@/types/event";
import sampleEvents from "@/data/sample-events.json";

export default function Home() {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const events = sampleEvents as Event[];

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      
      <main className="flex-1 w-full">
        <div className="max-w-4xl mx-auto px-4 py-6">
        <EventCalendar
          events={events}
          selectedDate={selectedDate}
          onSelectDate={setSelectedDate}
        />
        
        <EventList events={events} selectedDate={selectedDate} />
        </div>
      </main>
      
      <Footer />
    </div>
  );
}
