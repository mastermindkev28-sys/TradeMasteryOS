'use client';

import { useEffect } from 'react';

export default function QuantaraLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const prev = {
      bg: document.body.style.background,
      display: document.body.style.display,
      overflow: document.body.style.overflow,
    };
    document.body.style.background = '#0A0A0A';
    document.body.style.display = 'block';
    document.body.style.overflow = 'hidden auto';
    return () => {
      document.body.style.background = prev.bg;
      document.body.style.display = prev.display;
      document.body.style.overflow = prev.overflow;
    };
  }, []);

  return <>{children}</>;
}
