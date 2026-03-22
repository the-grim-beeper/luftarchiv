import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface GlossaryEntry {
  id: string;
  term: string;
  definition: string;
  category?: string;
  trust_level?: 'verified' | 'proposed' | 'ai_suggested' | string;
}

const TRUST_LEVELS = ['all', 'verified', 'proposed', 'ai_suggested'] as const;
const CATEGORIES = [
  'all',
  'rank',
  'unit_type',
  'incident_type',
  'aircraft',
  'fate',
  'other',
] as const;

const TRUST_STYLES: Record<string, string> = {
  verified: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  proposed: 'bg-amber-50 text-amber-700 border border-amber-200',
  ai_suggested: 'bg-indigo-50 text-indigo-700 border border-indigo-200',
};

const TRUST_LABELS: Record<string, string> = {
  verified: 'Verified',
  proposed: 'Proposed',
  ai_suggested: 'AI Suggested',
};

function TrustBadge({ level }: { level: string }) {
  const cls = TRUST_STYLES[level] ?? 'bg-slate-50 text-slate-500 border border-slate-200';
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-body font-medium ${cls}`}>
      {TRUST_LABELS[level] ?? level}
    </span>
  );
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded font-body text-xs transition-colors border ${
        active
          ? 'bg-archive-amber text-white border-archive-amber'
          : 'border-parchment text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber'
      }`}
    >
      {children}
    </button>
  );
}

export default function Knowledge() {
  const [entries, setEntries] = useState<GlossaryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trustFilter, setTrustFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadEntries = () => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (trustFilter !== 'all') params.trust_level = trustFilter;
    if (categoryFilter !== 'all') params.category = categoryFilter;
    api
      .listGlossary(params)
      .then((data) => setEntries(Array.isArray(data) ? data : data.items ?? []))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadEntries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trustFilter, categoryFilter]);

  const handleAction = async (id: string, action: 'approve' | 'demote') => {
    setActionLoading(id);
    try {
      await api.reviewGlossary(id, { action });
      await loadEntries();
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="font-heading text-3xl font-bold text-slate-ink mb-1">Knowledge Manager</h2>
        <p className="font-body text-slate-ink/50 text-sm">
          Review and curate glossary terms extracted from archive documents.
        </p>
      </div>

      {/* Filters */}
      <div className="mb-5 space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-body text-xs text-slate-ink/40 w-16 shrink-0">Trust</span>
          {TRUST_LEVELS.map((t) => (
            <FilterButton key={t} active={trustFilter === t} onClick={() => setTrustFilter(t)}>
              {t === 'ai_suggested' ? 'AI Suggested' : t.charAt(0).toUpperCase() + t.slice(1)}
            </FilterButton>
          ))}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-body text-xs text-slate-ink/40 w-16 shrink-0">Category</span>
          {CATEGORIES.map((c) => (
            <FilterButton
              key={c}
              active={categoryFilter === c}
              onClick={() => setCategoryFilter(c)}
            >
              {c === 'all'
                ? 'All'
                : c.replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase())}
            </FilterButton>
          ))}
        </div>
      </div>

      {error && <p className="font-body text-sm text-red-600 mb-4">Error: {error}</p>}

      {loading ? (
        <div className="py-16 text-center">
          <p className="font-body text-sm text-slate-ink/40">Loading glossary…</p>
        </div>
      ) : entries.length === 0 ? (
        <div className="border border-dashed border-parchment rounded-lg py-16 text-center">
          <p className="font-body text-sm text-slate-ink/40">No entries match the current filters.</p>
        </div>
      ) : (
        <div className="rounded-lg border border-parchment overflow-hidden">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-parchment/50 border-b border-parchment">
                <th className="px-4 py-3 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide w-40">
                  Term
                </th>
                <th className="px-4 py-3 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide">
                  Definition
                </th>
                <th className="px-4 py-3 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide w-28">
                  Category
                </th>
                <th className="px-4 py-3 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide w-28">
                  Trust
                </th>
                <th className="px-4 py-3 text-right font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide w-36">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, i) => (
                <tr
                  key={entry.id}
                  className={`border-b border-parchment/50 hover:bg-ivory/60 transition-colors ${
                    i % 2 === 0 ? 'bg-white' : 'bg-ivory/30'
                  }`}
                >
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm text-archive-amber font-semibold">
                      {entry.term}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-body text-sm text-slate-ink/80">
                    {entry.definition}
                  </td>
                  <td className="px-4 py-3 font-body text-xs text-slate-ink/50">
                    {entry.category
                      ? entry.category
                          .replace(/_/g, ' ')
                          .replace(/\b\w/g, (ch) => ch.toUpperCase())
                      : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {entry.trust_level ? <TrustBadge level={entry.trust_level} /> : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {entry.trust_level !== 'verified' && (
                        <button
                          onClick={() => handleAction(entry.id, 'approve')}
                          disabled={actionLoading === entry.id}
                          className="px-2.5 py-1 rounded border border-emerald-200 text-emerald-700 font-body text-xs hover:bg-emerald-50 transition-colors disabled:opacity-50"
                        >
                          Approve
                        </button>
                      )}
                      {entry.trust_level === 'verified' && (
                        <button
                          onClick={() => handleAction(entry.id, 'demote')}
                          disabled={actionLoading === entry.id}
                          className="px-2.5 py-1 rounded border border-amber-200 text-amber-700 font-body text-xs hover:bg-amber-50 transition-colors disabled:opacity-50"
                        >
                          Demote
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-3 font-body text-xs text-slate-ink/40 text-right">
        {entries.length} {entries.length === 1 ? 'entry' : 'entries'}
      </p>
    </div>
  );
}
