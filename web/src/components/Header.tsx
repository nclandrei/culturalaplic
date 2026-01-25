import { Logo } from "./Logo";

export function Header() {
  return (
    <header className="border-b-2 border-border bg-secondary-background py-4 px-4">
      <div className="max-w-4xl mx-auto flex items-center justify-between">
        <Logo />
        <div className="flex items-center gap-2" role="list" aria-label="Categorii evenimente">
          <div 
            className="w-9 h-9 md:w-10 md:h-10 bg-music border-2 border-border shadow-shadow flex items-center justify-center text-base md:text-lg"
            role="listitem"
            aria-label="Muzică"
          >
            <span aria-hidden="true">🎵</span>
          </div>
          <div 
            className="w-9 h-9 md:w-10 md:h-10 bg-theatre border-2 border-border shadow-shadow flex items-center justify-center text-base md:text-lg"
            role="listitem"
            aria-label="Teatru"
          >
            <span aria-hidden="true">🎭</span>
          </div>
          <div 
            className="w-9 h-9 md:w-10 md:h-10 bg-culture border-2 border-border shadow-shadow flex items-center justify-center text-base md:text-lg"
            role="listitem"
            aria-label="Cultură"
          >
            <span aria-hidden="true">🎨</span>
          </div>
        </div>
      </div>
    </header>
  );
}
