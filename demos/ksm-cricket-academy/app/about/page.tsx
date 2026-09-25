import Image from 'next/image';
import Link from 'next/link';
import { Trophy, Users, MapPin, CalendarBlank, ArrowRight } from '@phosphor-icons/react/dist/ssr';

const STATS = [
  { label: 'Active Members', value: '5,000+' },
  { label: 'Villages Covered', value: '200+' },
  { label: 'Constituencies', value: '5' },
  { label: 'Tournaments Per Year', value: '12+' },
];

const STAFF = [
  { name: 'K. Suresh Mohan', role: 'Head Coach', detail: '18 years coaching experience', seed: 'ksm-coach-1' },
  { name: 'Ravi Shankar', role: 'Batting Coach', detail: 'Former state-level player', seed: 'ksm-coach-2' },
  { name: 'Priya Nair', role: 'Administration Lead', detail: 'Managing KSM since 2018', seed: 'ksm-coach-3' },
];

export default function AboutPage() {
  return (
    <div className="min-h-[100dvh] bg-surface pt-16">

      {/* Hero */}
      <section className="relative py-28 bg-elevated border-b border-border overflow-hidden">
        <Image src="https://picsum.photos/seed/ksm-about-wide/1920/600" alt="" fill
          className="object-cover opacity-[0.06] mix-blend-luminosity" priority aria-hidden />
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-10">
          <span className="text-muted text-[11px] font-semibold uppercase tracking-[0.2em]">
            About KSM
          </span>
          <h1
            className="font-display font-black text-cream uppercase leading-none tracking-tight mt-4"
            style={{ fontSize: 'clamp(2.8rem, 8vw, 6rem)' }}
          >
            Building Cricket<br />Careers Since 2015
          </h1>
          <p className="mt-6 text-muted text-base max-w-xl leading-relaxed">
            Founded with one purpose: give every talented village cricketer a structured path to the state level.
          </p>
        </div>
      </section>

      {/* Stats */}
      <section className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-10">
          <div className="grid grid-cols-2 md:grid-cols-4">
            {STATS.map((stat, i) => (
              <div key={stat.label}
                className={`py-12 text-center ${i < STATS.length - 1 ? 'border-r border-border' : ''}`}>
                <div className="font-display font-black text-accent text-5xl sm:text-6xl">{stat.value}</div>
                <div className="text-muted text-[11px] uppercase tracking-[0.15em] mt-2">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Mission */}
      <section className="py-24 sm:py-32 border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="font-display font-black text-cream uppercase text-4xl sm:text-5xl tracking-tight mb-8">
                Our Mission
              </h2>
              <div className="space-y-4 text-muted text-sm leading-relaxed">
                <p>
                  Cricket talent is everywhere in India. It exists in small villages, in open fields, in gullies across the country. KSM Cricket Academy exists to make sure that talent has somewhere to go.
                </p>
                <p>
                  We built a three-tier system: Village, District, and State. A player in any of our 5 constituencies can start at the village level with just Rs. 100 and, if they perform, rise through the ranks to compete at the state level.
                </p>
                <p>
                  No player should miss their opportunity because of geography or access. KSM removes those barriers.
                </p>
              </div>

              <div className="mt-10 grid grid-cols-2 gap-4">
                {[
                  { icon: Trophy, label: 'Structured tournaments at every level' },
                  { icon: Users, label: 'Community-first membership model' },
                  { icon: MapPin, label: 'Coverage across 5 constituencies' },
                  { icon: CalendarBlank, label: 'Year-round cricket calendar' },
                ].map(({ icon: Icon, label }) => (
                  <div key={label} className="flex items-start gap-3">
                    <Icon size={16} className="text-accent shrink-0 mt-0.5" />
                    <span className="text-muted text-xs leading-relaxed">{label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative overflow-hidden border border-border" style={{ aspectRatio: '4/3' }}>
              <Image src="https://picsum.photos/seed/ksm-mission/800/600" alt="KSM Cricket training"
                fill className="object-cover grayscale" />
            </div>
          </div>
        </div>
      </section>

      {/* Journey detail */}
      <section className="py-24 sm:py-32 bg-elevated border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-10">
          <h2 className="font-display font-black text-cream uppercase text-4xl sm:text-5xl tracking-tight mb-16">
            How the Academy Works
          </h2>

          <div className="space-y-0">
            {[
              {
                level: 'Village Level',
                desc: 'Any registered KSM member can participate in village-level tournaments. Matches are held locally throughout the year. Performance is tracked against all other players in your constituency.',
              },
              {
                level: 'District Level',
                desc: 'Top performers from village tournaments are selected for district-level competition. Each constituency sends its best players to compete against others across the district.',
              },
              {
                level: 'State Level',
                desc: 'The KSM State Trophy brings together district champions from all constituencies. This is the highest level within the academy and the platform for scouting by state cricket boards.',
              },
            ].map(({ level, desc }, i) => (
              <div key={level}
                className={`border-t border-border py-8 grid grid-cols-1 sm:grid-cols-[14rem_1fr] gap-4 items-start ${
                  i === 2 ? 'border-b' : ''
                }`}>
                <h3 className="font-display font-bold text-cream uppercase text-xl tracking-tight">{level}</h3>
                <p className="text-muted text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Staff */}
      <section className="py-24 sm:py-32 border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-10">
          <h2 className="font-display font-black text-cream uppercase text-4xl sm:text-5xl tracking-tight mb-12">
            The Team
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {STAFF.map((person) => (
              <div key={person.name} className="bg-elevated border border-border overflow-hidden">
                <div className="relative h-52">
                  <Image src={`https://picsum.photos/seed/${person.seed}/400/300`} alt={person.name}
                    fill className="object-cover grayscale" />
                </div>
                <div className="p-6">
                  <h3 className="font-display font-bold text-cream uppercase text-xl tracking-tight mb-0.5">
                    {person.name}
                  </h3>
                  <p className="text-accent text-[11px] font-bold uppercase tracking-[0.15em] mb-2">
                    {person.role}
                  </p>
                  <p className="text-muted text-xs">{person.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contact + CTA */}
      <section className="py-24 sm:py-32 bg-elevated">
        <div className="max-w-7xl mx-auto px-4 sm:px-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-start">
            <div>
              <h2 className="font-display font-black text-cream uppercase text-4xl tracking-tight mb-6">
                Get in Touch
              </h2>
              <p className="text-muted text-sm mb-8 leading-relaxed">
                Questions about membership, tournaments, or the academy? Reach out and we will get back to you.
              </p>
              <div className="space-y-4 text-sm">
                {[
                  ['Phone', '+91 98765 43210'],
                  ['Email', 'info@ksmcricketacademy.in'],
                  ['Address', 'KSM Cricket Ground, India'],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-muted mb-0.5">{label}</p>
                    <p className="text-cream">{value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="border border-border p-10">
              <h3 className="font-display font-bold text-cream uppercase text-2xl tracking-tight mb-4">
                Ready to join?
              </h3>
              <p className="text-muted text-sm mb-8 leading-relaxed">
                Registration takes 3 minutes. Rs. 100 for a full year.
              </p>
              <Link href="/register"
                className="inline-flex items-center gap-2 bg-accent text-white font-bold text-xs px-8 py-4 uppercase tracking-[0.12em] hover:bg-red-700 transition-colors active:scale-[0.98]">
                Join Now <ArrowRight size={14} weight="bold" />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
