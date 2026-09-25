import Image from 'next/image';
import Link from 'next/link';
import { ArrowRight, Trophy, CalendarBlank, Users, MapPin } from '@phosphor-icons/react/dist/ssr';
import { TOURNAMENTS, GALLERY_IMAGES } from '@/lib/data';

export default function HomePage() {
  const previewImages = GALLERY_IMAGES.slice(0, 6);

  return (
    <>
      {/* ── Hero ────────────────────────────────────────────── */}
      <section className="relative min-h-[100dvh] flex flex-col justify-between bg-surface overflow-hidden">
        {/* Faint cricket ground image — very dark overlay */}
        <Image
          src="https://picsum.photos/seed/ksm-ground-wide/1920/1080"
          alt=""
          fill
          className="object-cover opacity-[0.08] mix-blend-luminosity"
          priority
          aria-hidden
        />

        {/* Top metadata bar */}
        <div className="relative z-10 flex items-center justify-between px-5 sm:px-10 pt-24">
          <span className="text-muted text-[11px] font-semibold uppercase tracking-[0.2em]">
            KSM Cricket Academy
          </span>
          <span className="text-muted text-[11px] font-semibold uppercase tracking-[0.2em]">
            Est. 2015
          </span>
        </div>

        {/* Main headline */}
        <div className="relative z-10 flex-1 flex flex-col justify-center px-4 sm:px-10 py-10">
          <h1
            className="font-display font-black uppercase leading-[0.88] tracking-tight"
            style={{ fontSize: 'clamp(4.5rem, 14vw, 11rem)' }}
          >
            <span className="block text-cream">Train</span>
            <span className="block text-cream">Compete</span>
            <span className="block text-accent">Excel.</span>
          </h1>

          <p className="mt-6 text-muted text-sm max-w-xs leading-relaxed">
            From village to state level. One membership.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/register"
              className="bg-accent text-white font-bold text-xs px-8 py-4 uppercase tracking-[0.12em] hover:bg-red-700 transition-colors active:scale-[0.98] inline-flex items-center gap-2"
            >
              Join Now
              <ArrowRight size={14} weight="bold" />
            </Link>
            <Link
              href="/about"
              className="border border-border text-muted text-xs font-bold px-8 py-4 uppercase tracking-[0.12em] hover:border-cream hover:text-cream transition-colors"
            >
              Learn More
            </Link>
          </div>
        </div>

        {/* Bottom rule */}
        <div className="relative z-10 border-t border-border mx-4 sm:mx-10 mb-8" />
      </section>

      {/* ── Journey ─────────────────────────────────────────── */}
      <section className="bg-elevated">
        <div className="max-w-7xl mx-auto">
          <div className="px-4 sm:px-10 pt-20 pb-6">
            <h2 className="font-display font-black text-cream uppercase text-4xl sm:text-5xl tracking-tight">
              The Journey
            </h2>
          </div>

          {[
            {
              no: '01',
              level: 'Village',
              desc: 'Register from your village. Compete locally. Build your record from the ground up.',
            },
            {
              no: '02',
              level: 'District',
              desc: 'Top performers advance to represent their district at the championship.',
            },
            {
              no: '03',
              level: 'State',
              desc: 'District champions compete for the KSM State Trophy. The highest level in the academy.',
            },
          ].map(({ no, level, desc }, i) => (
            <div
              key={no}
              className={`border-t border-border px-4 sm:px-10 py-8 grid grid-cols-[4rem_1fr] sm:grid-cols-[6rem_14rem_1fr] gap-4 sm:gap-8 items-start ${
                i === 2 ? 'border-b' : ''
              }`}
            >
              <span
                className="font-display font-black text-subtle text-5xl sm:text-6xl leading-none select-none"
              >
                {no}
              </span>
              <span className="font-display font-black text-cream uppercase text-2xl sm:text-3xl leading-tight pt-1">
                {level}
              </span>
              <p className="text-muted text-sm leading-relaxed col-span-2 sm:col-span-1 pt-0 sm:pt-2">
                {desc}
              </p>
            </div>
          ))}

          <div className="px-4 sm:px-10 pb-20 mt-6">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 text-accent text-xs font-bold uppercase tracking-[0.12em] hover:underline"
            >
              Start at village level
              <ArrowRight size={13} weight="bold" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Membership ──────────────────────────────────────── */}
      <section className="bg-surface border-t border-border py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <span className="text-muted text-[11px] font-semibold uppercase tracking-[0.2em]">
                Membership
              </span>
              <div className="mt-4 flex items-end gap-3 leading-none">
                <span
                  className="font-display font-black text-accent"
                  style={{ fontSize: 'clamp(5rem, 16vw, 9rem)' }}
                >
                  ₹100
                </span>
                <span className="text-muted text-sm font-semibold uppercase tracking-wide pb-4">
                  / year
                </span>
              </div>
              <p className="mt-4 text-muted text-sm leading-relaxed max-w-xs">
                One price. All levels. Every tournament. No hidden costs.
              </p>

              <Link
                href="/register"
                className="mt-10 inline-flex items-center gap-2 bg-accent text-white font-bold text-xs px-8 py-4 uppercase tracking-[0.12em] hover:bg-red-700 transition-colors active:scale-[0.98]"
              >
                Join Now
                <ArrowRight size={14} weight="bold" />
              </Link>
            </div>

            <div className="border border-border p-8">
              <p className="text-muted text-[11px] font-semibold uppercase tracking-[0.18em] mb-8">
                What you get
              </p>
              <ul className="space-y-5">
                {[
                  'Tournament access at village, district, and state level',
                  'Official KSM membership card',
                  'Performance record tracked across seasons',
                  'Coaching and training support',
                  'Priority registration for state events',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-4 text-sm text-muted">
                    <span className="w-1 h-1 rounded-full bg-accent mt-2 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>

              <div className="mt-8 pt-8 border-t border-border grid grid-cols-3 gap-4 text-center">
                {[
                  { v: '1 yr', l: 'Duration' },
                  { v: '5', l: 'Zones' },
                  { v: '3', l: 'Levels' },
                ].map(({ v, l }) => (
                  <div key={l}>
                    <p className="font-display font-black text-cream text-3xl">{v}</p>
                    <p className="text-muted text-[11px] uppercase tracking-wide mt-1">{l}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Tournaments ─────────────────────────────────────── */}
      <section className="bg-elevated border-t border-border py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-10">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-12">
            <h2 className="font-display font-black text-cream uppercase text-4xl sm:text-5xl tracking-tight">
              Tournaments
            </h2>
            <p className="text-muted text-sm max-w-xs">
              Three levels of competition throughout the year.
            </p>
          </div>

          <div className="space-y-0">
            {TOURNAMENTS.map((t, i) => {
              const levelColors: Record<string, string> = {
                village: 'text-pitch',
                district: 'text-blue-400',
                state: 'text-accent',
              };
              return (
                <div
                  key={t.id}
                  className={`border-t border-border py-8 grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-4 items-center ${
                    i === TOURNAMENTS.length - 1 ? 'border-b' : ''
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-4 mb-2">
                      <span className={`text-[11px] font-bold uppercase tracking-[0.15em] ${levelColors[t.level]}`}>
                        {t.level} level
                      </span>
                      <span className="text-[11px] text-muted uppercase tracking-wide">
                        {t.status}
                      </span>
                    </div>
                    <h3 className="font-display font-bold text-cream text-2xl sm:text-3xl uppercase tracking-tight">
                      {t.name}
                    </h3>
                    <div className="mt-3 flex flex-wrap gap-6 text-xs text-muted">
                      <span className="flex items-center gap-1.5">
                        <CalendarBlank size={13} className="text-muted" />
                        {new Date(t.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <MapPin size={13} className="text-muted" />
                        {t.location}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Users size={13} className="text-muted" />
                        {t.teams} teams
                      </span>
                    </div>
                  </div>
                  <Trophy size={28} className={levelColors[t.level]} />
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Gallery Preview ──────────────────────────────────── */}
      <section className="bg-surface border-t border-border py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-10">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-10">
            <h2 className="font-display font-black text-cream uppercase text-4xl sm:text-5xl tracking-tight">
              Gallery
            </h2>
            <Link
              href="/gallery"
              className="inline-flex items-center gap-1.5 text-accent text-xs font-bold uppercase tracking-[0.12em] hover:underline shrink-0"
            >
              All photos
              <ArrowRight size={13} weight="bold" />
            </Link>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-1.5">
            {previewImages.map((img, i) => (
              <div
                key={img.id}
                className={`relative overflow-hidden ${i === 0 ? 'row-span-2' : ''}`}
                style={{ aspectRatio: i === 0 ? '3/4' : '4/3' }}
              >
                <Image
                  src={`https://picsum.photos/seed/${img.seed}/${img.width}/${img.height}`}
                  alt={img.caption}
                  fill
                  className="object-cover hover:scale-105 transition-transform duration-700 grayscale hover:grayscale-0"
                />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────── */}
      <section className="bg-elevated border-t border-border py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-10">
          <div className="border border-border p-10 sm:p-16 flex flex-col sm:flex-row items-start sm:items-end justify-between gap-10">
            <div>
              <h2
                className="font-display font-black text-cream uppercase leading-none tracking-tight"
                style={{ fontSize: 'clamp(2.5rem, 7vw, 5.5rem)' }}
              >
                Ready?
              </h2>
              <p className="mt-4 text-muted text-sm max-w-xs leading-relaxed">
                Join thousands of players. Rs. 100 for a full year of cricket across 5 constituencies.
              </p>
            </div>
            <Link
              href="/register"
              className="bg-accent text-white font-bold text-sm px-10 py-5 uppercase tracking-[0.12em] hover:bg-red-700 transition-colors active:scale-[0.98] inline-flex items-center gap-3 shrink-0"
            >
              Join Now
              <ArrowRight size={16} weight="bold" />
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
