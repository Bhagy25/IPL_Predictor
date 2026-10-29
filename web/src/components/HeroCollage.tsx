import React from 'react';

export const HeroCollage: React.FC = () => {
  return (
    <section className="relative w-full overflow-hidden bg-[#070708] border-b border-white/[0.08]">
      {/* Accessible semantic heading for screen readers, SEO and accessibility */}
      <h1 className="sr-only">CricketLens — Historical IPL Analytics &amp; ML Predictions</h1>
      <p className="sr-only">The game through a different lens. Explore · Analyze · Predict · Discover</p>

      {/* Hero Artwork Stage */}
      <div className="relative w-full max-w-[1440px] mx-auto flex flex-col items-center">
        {/*
          Approved Figma exports, one per breakpoint; the browser downloads only the one it shows.
          From 768px: hero-desktop.png (1024 x 369), drawn at most 992 CSS px wide (the 1024px frame less its
          padding), so it is scaled slightly rather than mapped 1:1. Below 768px: hero-mobile.png (780 x 968),
          drawn at most 366 CSS px wide, about 2.1 image pixels per CSS pixel.
        */}
        <div className="w-full max-w-[390px] overflow-hidden pt-2 pb-6 px-3 md:max-w-[1024px] md:pt-1 md:pb-4 md:px-4">
          <picture>
            <source media="(min-width: 768px)" srcSet="/assets/hero-desktop.png" width={1024} height={369} />
            <img
              src="/assets/hero-mobile.png"
              alt="CricketLens — Historical IPL Analytics & ML Predictions"
              className="w-full h-auto object-contain object-top"
              width={780}
              height={968}
              loading="eager"
              decoding="sync"
            />
          </picture>
        </div>
      </div>
    </section>
  );
};
