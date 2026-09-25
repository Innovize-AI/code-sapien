'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { List, X, Trophy } from '@phosphor-icons/react';

const links = [
  { href: '/', label: 'Home' },
  { href: '/about', label: 'About' },
  { href: '/gallery', label: 'Gallery' },
  { href: '/members', label: 'Members' },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      ([entry]) => setScrolled(!entry.isIntersecting),
      { threshold: 0 }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  useEffect(() => { setOpen(false); }, [pathname]);

  return (
    <>
      <div ref={sentinelRef} className="absolute top-0 h-px w-full pointer-events-none" />
      <header
        className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
          scrolled
            ? 'bg-surface border-b border-border'
            : 'bg-transparent'
        }`}
      >
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 font-display font-black text-lg text-cream uppercase tracking-wide hover:text-accent transition-colors"
          >
            <Trophy size={20} weight="fill" className="text-accent" />
            KSM Cricket
          </Link>

          <div className="hidden md:flex items-center gap-8">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-xs font-semibold uppercase tracking-[0.12em] transition-colors ${
                  pathname === link.href
                    ? 'text-accent'
                    : 'text-muted hover:text-cream'
                }`}
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/register"
              className="bg-accent text-white text-xs font-bold px-5 py-2.5 uppercase tracking-[0.1em] hover:bg-red-700 transition-colors active:scale-[0.98]"
            >
              Join Now
            </Link>
          </div>

          <button
            onClick={() => setOpen(!open)}
            className="md:hidden p-2 text-cream"
            aria-label="Toggle menu"
          >
            {open ? <X size={22} /> : <List size={22} />}
          </button>
        </nav>

        {open && (
          <div className="md:hidden bg-surface border-t border-border px-4 pb-5 pt-3 flex flex-col gap-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-xs font-semibold uppercase tracking-[0.12em] py-3 px-2 transition-colors ${
                  pathname === link.href ? 'text-accent' : 'text-muted hover:text-cream'
                }`}
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/register"
              className="bg-accent text-white text-xs font-bold px-4 py-3.5 uppercase tracking-[0.1em] text-center mt-3"
            >
              Join Now
            </Link>
          </div>
        )}
      </header>
    </>
  );
}
