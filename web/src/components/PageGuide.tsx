import React from 'react';
import { Info } from 'lucide-react';
import { FOCUS_RING } from './player/playerFormat';

/**
 * A short, presentation-friendly explanation under a page title: what the page shows (always visible) and
 * how to read it (expandable). Text only, no numbers: every figure on the site comes from the API.
 */
export const PageGuide: React.FC<{ shows: React.ReactNode; read: React.ReactNode[]; terms?: [string, string][] }> = ({ shows, read, terms }) => (
  <section aria-label="About this page" className="bg-[#101114] border border-[#D9B15F]/15 rounded-2xl p-4 sm:p-5 space-y-2">
    <p className="text-xs sm:text-sm text-[#B9B9B3] flex items-start gap-2">
      <Info className="w-4 h-4 text-[#D9B15F] shrink-0 mt-0.5" aria-hidden="true" />
      <span><strong className="text-[#F6F6F3]">What this page shows: </strong>{shows}</span>
    </p>
    <details className="text-xs text-[#B9B9B3] ml-6">
      <summary className={`cursor-pointer font-semibold text-[#D9B15F] w-fit ${FOCUS_RING}`}>How to read it</summary>
      <ul className="list-disc ml-5 mt-2 space-y-1">{read.map((r, i) => <li key={i}>{r}</li>)}</ul>
      {terms && terms.length > 0 && (
        <dl className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
          {terms.map(([t, d]) => (
            <div key={t}>
              <dt className="inline font-semibold text-[#F6F6F3]">{t}: </dt>
              <dd className="inline">{d}</dd>
            </div>
          ))}
        </dl>
      )}
    </details>
  </section>
);
