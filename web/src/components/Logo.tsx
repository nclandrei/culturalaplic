import Image from "next/image";
import Link from "next/link";

export function Logo() {
  return (
    <Link href="/" className="group flex items-center gap-4">
      <Image
        src="/logo.png"
        alt="Cultură la plic"
        width={64}
        height={64}
        className="rounded-base border-2 border-border shadow-shadow"
      />
      <span className="relative text-2xl md:text-3xl font-bold tracking-tight">
        Cultură la plic
        <span className="absolute -bottom-1 left-0 w-0 h-2 bg-culture -rotate-1 group-hover:w-full transition-all duration-300" />
      </span>
    </Link>
  );
}
