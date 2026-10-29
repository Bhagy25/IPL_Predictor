import React from 'react';

export const HeroCollage: React.FC = () => {
  return (
    <section className="relative w-full overflow-hidden bg-[#070708] border-b border-white/[0.08]">
      {/* Accessible semantic heading for screen readers, SEO and accessibility */}
      <h1 className="sr-only">CricketLens — Historical IPL Analytics &amp; ML Predictions</h1>
      <p className="sr-only">The game through a different lens. Explore · Analyze · Predict · Discover</p>

      {/* Hero Artwork Stage */}
      <div className="relative w-full max-w-[1440px] mx-auto flex flex-col items-center">
        
        {/* Desktop Hero Artwork (Figma approved high-resolution export, displayed at native 1:1 pixel mapping) */}
        <div className="hidden md:block w-full max-w-[1024px] overflow-hidden pt-1 pb-4 px-2 sm:px-4">
          <img
            src="/assets/hero-desktop.png"
            alt="CricketLens — Historical IPL Analytics & ML Predictions"
            className="w-full h-auto object-contain object-top"
            width={1024}
            height={369}
            loading="eager"
            decoding="sync"
          />
        </div>

        {/* Mobile Hero Artwork (Figma approved high-resolution export, crisp @2x density on mobile) */}
        <div className="block md:hidden w-full max-w-[390px] overflow-hidden pt-2 pb-6 px-3">
          <img
            src="/assets/hero-mobile.png"
            alt="CricketLens — Historical IPL Analytics & ML Predictions"
            className="w-full h-auto object-contain object-top"
            width={780}
            height={968}
            loading="eager"
            decoding="sync"
          />
        </div>

      </div>
    </section>
  );
};
