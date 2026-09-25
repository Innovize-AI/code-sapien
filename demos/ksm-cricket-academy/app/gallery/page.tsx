'use client';

import { useState } from 'react';
import Image from 'next/image';
import { X } from '@phosphor-icons/react';
import { GALLERY_IMAGES } from '@/lib/data';

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'training', label: 'Training' },
  { id: 'tournaments', label: 'Tournaments' },
  { id: 'events', label: 'Events' },
];

export default function GalleryPage() {
  const [active, setActive] = useState('all');
  const [lightbox, setLightbox] = useState<string | null>(null);

  const filtered = active === 'all' ? GALLERY_IMAGES : GALLERY_IMAGES.filter((img) => img.category === active);

  return (
    <div className="min-h-[100dvh] bg-surface pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">

        <div className="mb-10">
          <h1 className="font-display font-black text-cream uppercase text-4xl sm:text-5xl tracking-tight mb-2">
            Gallery
          </h1>
          <p className="text-muted text-sm">Training, tournaments, and life at KSM.</p>
        </div>

        {/* Category tabs */}
        <div className="flex gap-2 flex-wrap mb-8 border-b border-border pb-4">
          {CATEGORIES.map((cat) => (
            <button key={cat.id} onClick={() => setActive(cat.id)}
              className={`px-4 py-2 text-xs font-bold uppercase tracking-[0.12em] transition-colors ${
                active === cat.id
                  ? 'bg-accent text-white'
                  : 'border border-border text-muted hover:border-cream hover:text-cream'
              }`}>
              {cat.label}
            </button>
          ))}
        </div>

        {/* Masonry grid */}
        <div className="columns-2 md:columns-3 lg:columns-4 gap-1.5 space-y-1.5">
          {filtered.map((img) => (
            <div key={img.id}
              className="break-inside-avoid overflow-hidden cursor-pointer relative group"
              onClick={() => setLightbox(`https://picsum.photos/seed/${img.seed}/${img.width}/${img.height}`)}>
              <Image
                src={`https://picsum.photos/seed/${img.seed}/${img.width}/${img.height}`}
                alt={img.caption}
                width={img.width}
                height={img.height}
                className="w-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500 group-hover:scale-105"
              />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-300" />
            </div>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-20 text-muted text-sm uppercase tracking-wide">
            No photos in this category yet.
          </div>
        )}
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center p-4"
          onClick={() => setLightbox(null)}>
          <button onClick={() => setLightbox(null)}
            className="absolute top-4 right-4 text-cream p-2 border border-border hover:border-cream transition-colors"
            aria-label="Close">
            <X size={20} />
          </button>
          <div className="relative max-w-4xl w-full max-h-[85vh]" onClick={(e) => e.stopPropagation()}>
            <Image src={lightbox} alt="Gallery image" width={1200} height={900}
              className="w-full h-auto max-h-[85vh] object-contain" />
          </div>
        </div>
      )}
    </div>
  );
}
