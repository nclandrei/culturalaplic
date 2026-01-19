export function Header() {
  return (
    <header className="border-b-2 border-border bg-secondary-background py-6 px-4 overflow-hidden">
      <div className="max-w-4xl mx-auto relative">
        {/* Decorative floating shapes */}
        <div className="absolute -top-2 -left-4 w-8 h-8 bg-music border-2 border-border rounded-full hidden md:block" />
        <div className="absolute top-8 -left-8 w-5 h-5 bg-theatre border-2 border-border rotate-45 hidden md:block" />
        <div className="absolute -top-1 right-12 w-6 h-6 bg-culture border-2 border-border hidden md:block" />
        <div className="absolute top-10 -right-2 w-4 h-4 bg-music border-2 border-border rounded-full hidden md:block" />
        
        {/* Main title block */}
        <div className="relative z-10">
          <div className="inline-block">
            <h1 className="text-3xl md:text-5xl font-bold tracking-tight leading-none">
              <span className="relative">
                Calendarul
                <span className="absolute -bottom-1 left-0 w-full h-2 bg-culture -z-10 -rotate-1" />
              </span>
            </h1>
            <h1 className="text-3xl md:text-5xl font-bold tracking-tight leading-none mt-1">
              <span className="relative inline-block ml-4 md:ml-8">
                Hipsterului
                <span className="absolute -bottom-1 left-0 w-full h-2 bg-theatre -z-10 rotate-1" />
              </span>
            </h1>
          </div>
          
          {/* Tagline in a tilted box */}
          <div className="mt-4 inline-block">
            <div className="bg-music text-white border-2 border-border px-4 py-1.5 shadow-shadow rotate-[-2deg] inline-block">
              <p className="text-sm md:text-base font-medium">
                ✨ Ce faci în weekend?
              </p>
            </div>
          </div>
        </div>
        
        {/* Decorative icons representing categories */}
        <div className="absolute right-0 top-1/2 -translate-y-1/2 hidden lg:flex flex-col gap-2">
          <div className="w-10 h-10 bg-music border-2 border-border shadow-shadow flex items-center justify-center text-lg">
            🎵
          </div>
          <div className="w-10 h-10 bg-theatre border-2 border-border shadow-shadow flex items-center justify-center text-lg -ml-3">
            🎭
          </div>
          <div className="w-10 h-10 bg-culture border-2 border-border shadow-shadow flex items-center justify-center text-lg">
            🎨
          </div>
        </div>
      </div>
    </header>
  );
}
