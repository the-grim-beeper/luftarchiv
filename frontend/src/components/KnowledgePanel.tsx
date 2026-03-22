import { useState } from 'react';

interface GlossaryTerm {
  id: string;
  term: string;
  definition: string;
  category?: string;
  trust_level?: 'verified' | 'proposed' | 'ai_suggested' | string;
}

interface KnowledgePanelProps {
  terms: GlossaryTerm[];
}

const TRUST_STYLES: Record<string, string> = {
  verified: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  proposed: 'bg-amber-50 text-amber-700 border border-amber-200',
  ai_suggested: 'bg-indigo-50 text-indigo-700 border border-indigo-200',
};

function TrustBadge({ level }: { level: string }) {
  const cls = TRUST_STYLES[level] ?? 'bg-slate-50 text-slate-500 border border-slate-200';
  const label =
    level === 'ai_suggested' ? 'AI' : level === 'proposed' ? 'Proposed' : 'Verified';
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-body font-medium ${cls}`}>
      {label}
    </span>
  );
}

export default function KnowledgePanel({ terms }: KnowledgePanelProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-t border-parchment bg-white">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-ivory/50 transition-colors"
      >
        <span className="font-body text-sm font-medium text-slate-ink/70">
          Glossary — {terms.length} {terms.length === 1 ? 'term' : 'terms'} on this page
        </span>
        <span className="font-mono text-xs text-slate-ink/40 select-none">
          {open ? '▲' : '▼'}
        </span>
      </button>

      {open && (
        <div className="px-5 pb-4 max-h-48 overflow-y-auto">
          {terms.length === 0 ? (
            <p className="font-body text-xs text-slate-ink/40 py-2">
              No glossary terms matched for this page.
            </p>
          ) : (
            <div className="space-y-2">
              {terms.map((t) => (
                <div key={t.id} className="flex items-start gap-3">
                  <span className="font-mono text-xs text-archive-amber font-semibold w-20 shrink-0 mt-0.5">
                    {t.term}
                  </span>
                  <span className="font-body text-xs text-slate-ink/70 flex-1">{t.definition}</span>
                  {t.trust_level && <TrustBadge level={t.trust_level} />}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
