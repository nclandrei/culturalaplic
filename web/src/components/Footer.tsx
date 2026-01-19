import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t-2 border-border bg-secondary-background py-6 px-4 mt-auto">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm">
        <div className="flex items-center gap-4">
          <Link 
            href="/despre" 
            className="hover:underline underline-offset-2"
          >
            Despre
          </Link>
          <a 
            href="mailto:andrei@nicolaeandrei.com" 
            className="hover:underline underline-offset-2"
          >
            Contact
          </a>
        </div>
        
        <p className="text-foreground/70">
          Făcut cu ☕ în București
        </p>
      </div>
    </footer>
  );
}
