import Link from 'next/link';
import { Trophy, Phone, EnvelopeSimple, MapPin } from '@phosphor-icons/react/dist/ssr';

export default function Footer() {
  return (
    <footer className="bg-surface border-t border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-10 py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
          <div className="md:col-span-2">
            <Link href="/" className="inline-flex items-center gap-2 font-display font-black text-lg text-cream uppercase tracking-wide mb-4">
              <Trophy size={20} weight="fill" className="text-accent" />
              KSM Cricket Academy
            </Link>
            <p className="text-muted text-sm leading-relaxed max-w-xs mt-2">
              Building cricket careers from village to state level across 5 constituencies.
            </p>
            <div className="mt-6 space-y-2 text-xs text-muted">
              <div className="flex items-center gap-2">
                <Phone size={13} className="text-accent shrink-0" />
                <span>+91 98765 43210</span>
              </div>
              <div className="flex items-center gap-2">
                <EnvelopeSimple size={13} className="text-accent shrink-0" />
                <span>info@ksmcricketacademy.in</span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin size={13} className="text-accent shrink-0" />
                <span>KSM Ground, India</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-cream text-[11px] font-semibold uppercase tracking-[0.18em] mb-5">Pages</h3>
            <ul className="space-y-3 text-xs text-muted">
              {[
                { href: '/', label: 'Home' },
                { href: '/about', label: 'About Us' },
                { href: '/gallery', label: 'Gallery' },
                { href: '/members', label: 'Members' },
                { href: '/register', label: 'Register' },
              ].map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="hover:text-cream transition-colors uppercase tracking-[0.1em] font-medium">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-cream text-[11px] font-semibold uppercase tracking-[0.18em] mb-5">Constituencies</h3>
            <ul className="space-y-3 text-xs text-muted uppercase tracking-[0.1em] font-medium">
              <li>North Zone</li>
              <li>South Zone</li>
              <li>East Zone</li>
              <li>West Zone</li>
              <li>Central Zone</li>
            </ul>
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-subtle uppercase tracking-[0.12em]">
          <span>2025 KSM Cricket Academy</span>
          <span>ksmcricketacademy.in</span>
        </div>
      </div>
    </footer>
  );
}
