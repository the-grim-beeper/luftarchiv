import { useState } from 'react';
import { Link } from 'react-router-dom';

interface SearchRecord {
  id: string;
  entry_number?: string | number;
  date?: string;
  unit?: string;
  aircraft?: string;
  incident_type?: string;
  damage_level?: number;
  personnel?: Array<{ name?: string; fate?: string }>;
  page_id?: string;
  collection_id?: string;
  page_number?: number;
}

interface RecordTableProps {
  records: SearchRecord[];
}

type SortKey = 'date' | 'unit' | 'aircraft' | 'incident_type';

function DamageBar({ level }: { level?: number }) {
  if (level === undefined || level === null) return <span className="text-slate-ink/30">—</span>;
  const pct = Math.min(100, Math.max(0, level));
  const color = pct >= 75 ? 'bg-red-500' : pct >= 40 ? 'bg-amber-500' : 'bg-emerald-500';
  return (
    <div className="flex items-center gap-1.5 min-w-[5rem]">
      <div className="flex-1 h-1.5 bg-parchment rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-slate-ink/50 w-7 text-right">{pct}%</span>
    </div>
  );
}

export default function RecordTable({ records }: RecordTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('date');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  if (records.length === 0) {
    return (
      <div className="border border-dashed border-parchment rounded-lg py-16 text-center">
        <p className="font-body text-sm text-slate-ink/40">No results found. Try a different query.</p>
      </div>
    );
  }

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const sorted = [...records].sort((a, b) => {
    const av = (a[sortKey] ?? '') as string;
    const bv = (b[sortKey] ?? '') as string;
    return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
  });

  const SortIcon = ({ k }: { k: SortKey }) => (
    <span className="ml-1 text-slate-ink/30">
      {sortKey === k ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
    </span>
  );

  const Th = ({
    children,
    sortable,
    k,
  }: {
    children: React.ReactNode;
    sortable?: boolean;
    k?: SortKey;
  }) => (
    <th
      onClick={sortable && k ? () => toggleSort(k) : undefined}
      className={`px-3 py-2.5 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide whitespace-nowrap ${
        sortable ? 'cursor-pointer hover:text-archive-amber select-none' : ''
      }`}
    >
      {children}
      {sortable && k && <SortIcon k={k} />}
    </th>
  );

  return (
    <div className="overflow-x-auto rounded-lg border border-parchment">
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-parchment/50 border-b border-parchment">
            <Th>#</Th>
            <Th sortable k="date">Date</Th>
            <Th sortable k="unit">Unit</Th>
            <Th sortable k="aircraft">Aircraft</Th>
            <Th sortable k="incident_type">Incident</Th>
            <Th>Damage</Th>
            <Th>Personnel</Th>
            <Th>Source</Th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => (
            <tr
              key={r.id}
              className={`border-b border-parchment/50 hover:bg-ivory/60 transition-colors ${
                i % 2 === 0 ? 'bg-white' : 'bg-ivory/30'
              }`}
            >
              <td className="px-3 py-2 font-mono text-xs text-slate-ink/40">
                {r.entry_number ?? i + 1}
              </td>
              <td className="px-3 py-2 font-body text-xs text-slate-ink/80 whitespace-nowrap">
                {r.date ?? '—'}
              </td>
              <td className="px-3 py-2 font-body text-xs text-slate-ink/80">{r.unit ?? '—'}</td>
              <td className="px-3 py-2 font-body text-xs text-slate-ink/80">{r.aircraft ?? '—'}</td>
              <td className="px-3 py-2 font-body text-xs text-slate-ink/80">
                {r.incident_type ?? '—'}
              </td>
              <td className="px-3 py-2">
                <DamageBar level={r.damage_level} />
              </td>
              <td className="px-3 py-2 font-body text-xs text-slate-ink/70 max-w-[12rem]">
                {r.personnel && r.personnel.length > 0
                  ? r.personnel.map((p) => p.name ?? '').filter(Boolean).join(', ') || '—'
                  : '—'}
              </td>
              <td className="px-3 py-2">
                <Link
                  to={`/viewer/${r.page_id}`}
                  className="font-body text-xs text-archive-amber hover:underline"
                >
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
