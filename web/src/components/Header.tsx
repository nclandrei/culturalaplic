export function Header() {
  return (
    <header className="border-b-2 border-border bg-secondary-background py-6 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl md:text-5xl font-bold tracking-tight leading-none">
            <span className="relative">
              Cultură la plic
              <span className="absolute -bottom-0.5 left-0 w-full h-3 bg-culture -z-10 -rotate-1" />
            </span>
          </h1>
          
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 md:w-10 md:h-10 bg-music border-2 border-border shadow-shadow flex items-center justify-center text-base md:text-lg">
              🎵
            </div>
            <div className="w-9 h-9 md:w-10 md:h-10 bg-theatre border-2 border-border shadow-shadow flex items-center justify-center text-base md:text-lg">
              🎭
            </div>
            <div className="w-9 h-9 md:w-10 md:h-10 bg-culture border-2 border-border shadow-shadow flex items-center justify-center text-base md:text-lg">
              🎨
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
