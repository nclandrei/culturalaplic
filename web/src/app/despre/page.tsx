import { Header } from "@/components/Header";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Despre | Cultură la plic",
  description: "Ce este Cultură la plic și de unde vin datele",
};

const sources = {
  music: [
    { name: "Ateneul Român", url: "https://filarmonicaenescu.ro" },
    { name: "Bikers For Humanity Rock Fest", url: "https://bikersforhumanity.ro" },
    { name: "Control Club", url: "https://control-club.ro" },
    { name: "Expirat", url: "https://expirat.org" },
    { name: "Festivalul George Enescu", url: "https://festivalenescu.ro" },
    { name: "Gărâna Jazz Festival", url: "https://garana-jazz.ro" },
    { name: "Hard Rock Cafe Bucharest", url: "https://cafe.hardrock.com/bucharest" },
    { name: "Jazz Fan Rising", url: "https://eventbook.ro/program/jazz-fan-rising" },
    { name: "Jazz in the Park", url: "https://jazzinthepark.ro" },
    { name: "JAZZx Festival", url: "https://plai.ro/jazz" },
    { name: "Opera Națională București", url: "https://operanb.ro" },
    { name: "Quantic", url: "https://quantic.ro" },
    { name: "Rockstadt Extreme Fest", url: "https://rockstadtextremefest.ro" },
  ],
  theatre: [
    { name: "Cuibul Artiștilor", url: "https://cuibul.ro" },
    { name: "Godot Cafe Teatru", url: "https://godotcafe.ro" },
    { name: "Grivița 53", url: "https://grivita53.ro" },
    { name: "Teatrul Bulandra", url: "https://bulandra.ro" },
    { name: "Teatrul Metropolis", url: "https://teatrulmetropolis.ro" },
    { name: "Teatrul Mic", url: "https://teatrulmic.ro" },
    { name: "Teatrul Național București", url: "https://tnb.ro" },
    { name: "Teatrul Nottara", url: "https://nottara.ro" },
  ],
  culture: [
    { name: "ARCUB", url: "https://arcub.ro" },
    { name: "Cinema Elvire Popesco", url: "https://eventbook.ro/elvirepopesco" },
    { name: "Improteca", url: "https://improteca.ro" },
    { name: "MARe", url: "https://mare.ro" },
    { name: "MNAC", url: "https://mnac.ro" },
  ],
};

export default function DesprePage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Despre</h1>

        <section className="mb-8">
          <p className="text-lg leading-relaxed mb-4">
            <strong>Cultură la plic</strong> agregă evenimente culturale din București într-un singur loc. 
            Concerte, spectacole de teatru, expoziții — tot ce ai nevoie ca să-ți planifici weekendul.
          </p>
          <p className="text-lg leading-relaxed">
            Datele sunt colectate automat din sursele de mai jos și actualizate zilnic.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-music border-2 border-border shadow-shadow flex items-center justify-center text-sm">
              🎵
            </span>
            Muzică
          </h2>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {sources.music.map((source) => (
              <li key={source.name}>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline underline-offset-2"
                >
                  {source.name} ↗
                </a>
              </li>
            ))}
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-theatre border-2 border-border shadow-shadow flex items-center justify-center text-sm">
              🎭
            </span>
            Teatru
          </h2>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {sources.theatre.map((source) => (
              <li key={source.name}>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline underline-offset-2"
                >
                  {source.name} ↗
                </a>
              </li>
            ))}
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span className="w-8 h-8 bg-culture border-2 border-border shadow-shadow flex items-center justify-center text-sm">
              🎨
            </span>
            Cultură
          </h2>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {sources.culture.map((source) => (
              <li key={source.name}>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline underline-offset-2"
                >
                  {source.name} ↗
                </a>
              </li>
            ))}
          </ul>
        </section>

        <section className="border-t-2 border-border pt-6">
          <p className="text-foreground/70">
            Întrebări? Scrie-mi la{" "}
            <a 
              href="mailto:andrei@nicolaeandrei.com" 
              className="underline underline-offset-2"
            >
              andrei@nicolaeandrei.com
            </a>
          </p>
        </section>
      </main>
    </div>
  );
}
