import { useState, useRef } from 'react';

interface ScanViewerProps {
  imagePath: string | null;
}

export default function ScanViewer({ imagePath }: ScanViewerProps) {
  const [scale, setScale] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);

  if (!imagePath) {
    return (
      <div className="flex items-center justify-center h-full bg-parchment/30 border border-parchment rounded-lg">
        <p className="font-body text-sm text-slate-ink/30">No scan available</p>
      </div>
    );
  }

  const src = `/api/collections/pages/image?path=${encodeURIComponent(imagePath)}`;

  const zoomIn = () => setScale((s) => Math.min(s + 0.25, 4));
  const zoomOut = () => setScale((s) => Math.max(s - 0.25, 0.25));
  const resetZoom = () => setScale(1);

  return (
    <div className="flex flex-col h-full">
      {/* Zoom controls */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-parchment bg-white/80 shrink-0">
        <button
          onClick={zoomOut}
          className="w-7 h-7 flex items-center justify-center rounded border border-parchment text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors font-body text-sm"
          title="Zoom out"
        >
          −
        </button>
        <button
          onClick={resetZoom}
          className="px-2 h-7 flex items-center justify-center rounded border border-parchment text-xs font-mono text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors min-w-[3.5rem]"
          title="Reset zoom"
        >
          {Math.round(scale * 100)}%
        </button>
        <button
          onClick={zoomIn}
          className="w-7 h-7 flex items-center justify-center rounded border border-parchment text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors font-body text-sm"
          title="Zoom in"
        >
          +
        </button>
      </div>

      {/* Image container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto bg-slate-ink/5 rounded-b-lg"
      >
        <div
          className="min-h-full flex items-start justify-center p-4"
          style={{ minWidth: `${scale * 100}%` }}
        >
          <img
            src={src}
            alt="Archive scan"
            style={{ transform: `scale(${scale})`, transformOrigin: 'top center' }}
            className="max-w-full shadow-md border border-parchment"
            draggable={false}
          />
        </div>
      </div>
    </div>
  );
}
