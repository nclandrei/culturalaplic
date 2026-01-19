import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Despre | Cultură la plic",
  description: "Ce este Cultură la plic și de unde vin datele",
};

const sources = {
  music: [
    { name: "Control Club", url: "https://control-club.ro" },
    { name: "Expirat", url: "https://expirat.org" },
    { name: "Quantic", url: "https://quantic.ro" },
    { name: "Hard Rock Cafe", url: "https://hardrockcafe.com/location/bucharest" },
    { name: "JFR", url: "https://jfrclub.ro" },
    { name: "Opera Națională București", url: "https://operanb.ro" },
    { name: "iaBilet", url: "https://www.iabilet.ro" },
    { name: "Eventbook", url: "https://eventbook.ro" },
  ],
  theatre: [
    { name: "Teatrul Bulandra", url: "https://bulandra.ro" },
    { name: "Teatrul Nottara", url: "https://nottara.ro" },
    { name: "Teatrul Național București", url: "https://tnb.ro" },
    { name: "Teatrul Metropolis", url: "https://teatrulmetropolis.ro" },
    { name: "Teatrul Mic", url: "https://teatrulmic.ro" },
    { name: "Godot Cafe Teatru", url: "https://godotcafe.ro" },
    { name: "Grivița 53", url: "https://grivita53.ro" },
    { name: "Cuibul Artiștilor", url: "https://cuibul.ro" },
  ],
  culture: [
    { name: "ARCUB", url: "https://arcub.ro" },
    { name: "MNAC", url: "https://mnac.ro" },
    { name: "Improteca", url: "https://improteca.ro" },
  ],
};

export default function DesprePage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b-2 border-border bg-secondary-background py-6 px-4">
        <div className="max-w-4xl mx-auto">
          <Link 
            href="/" 
            className="text-2xl md:text-3xl font-bold tracking-tight hover:opacity-80 transition-opacity"
          >
            <span className="relative">
              Cultură la plic
              <span className="absolute -bottom-0.5 left-0 w-full h-2 bg-culture -z-10 -rotate-1" />
            </span>
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Despre</h1>

        <section className="mb-8">
          <p className="text-lg leading-relaxed mb-4">
            <strong>Cultură la plic</strong> agregă evenimente culturale din București într-un singur loc. 
            Concerte, spectacole de teatru, expoziții, stand-up — tot ce ai nevoie ca să-ți planifici weekendul.
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
