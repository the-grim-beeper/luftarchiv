import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface GlossaryEntry {
  id: string;
  term: string;
  definition: string;
  category?: string;
  trust_level?: string;
}

interface KnowledgePanelProps {
  terms: string[];
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
  const [entries, setEntries] = useState<GlossaryEntry[]>([]);

  useEffect(() => {
    if (terms.length === 0) {
      setEntries([]);
      return;
    }
    // Fetch all glossary entries and filter to matching terms
    api.listGlossary().then((data: any) => {
      const allEntries: GlossaryEntry[] = data.items ?? data.entries ?? data ?? [];
      const termLower = new Set(terms.map((t) => t.toLowerCase()));
      const matched = allEntries.filter((e) => termLower.has(e.term.toLowerCase()));
      setEntries(matched);
    });
  }, [terms.join(',')]);

  const count = entries.length;

  return (
    <div className="border-t border-parchment bg-white">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-ivory/50 transition-colors"
      >
        <span className="font-body text-sm font-medium text-slate-ink/70">
          Glossary — {count} {count === 1 ? 'term' : 'terms'} on this page
        </span>
        <span className="font-mono text-xs text-slate-ink/40 select-none">
          {open ? '▲' : '▼'}
        </span>
      </button>

      {open && (
        <div className="px-5 pb-4 max-h-48 overflow-y-auto">
          {entries.length === 0 ? (
            <p className="font-body text-xs text-slate-ink/40 py-2">
              No glossary terms matched for this page.
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
              {entries.map((e) => (
                <div key={e.id} className="flex items-start gap-3">
                  <span className="font-mono text-xs text-archive-amber font-semibold shrink-0 mt-0.5">
                    {e.term}
                  </span>
                  <span className="font-body text-xs text-slate-ink/70 flex-1">{e.definition}</span>
                  {e.trust_level && <TrustBadge level={e.trust_level} />}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
