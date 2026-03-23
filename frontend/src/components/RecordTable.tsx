import { useState } from 'react';
import { Link } from 'react-router-dom';

interface SearchRecord {
  id: string;
  entry_number?: number;
  date?: string;
  unit_designation?: string;
  aircraft_type?: string;
  incident_type?: string;
  damage_percentage?: number;
  location?: string;
  werknummer?: string;
  personnel?: Array<{
    rank_abbreviation?: string;
    surname?: string;
    first_name?: string;
    fate_english?: string;
  }>;
  page_id?: string;
  collection_id?: string;
  page_number?: number;
}

interface RecordTableProps {
  records: SearchRecord[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

type SortKey = 'date' | 'unit_designation' | 'aircraft_type' | 'incident_type';

function DamageBar({ level }: { level?: number }) {
  if (level === undefined || level === null) return <span className="text-slate-ink/20">—</span>;
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

export default function RecordTable({ records, total, page, pageSize, onPageChange }: RecordTableProps) {
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

  const totalPages = Math.ceil(total / pageSize);

  const personnelStr = (r: SearchRecord) => {
    if (!r.personnel || r.personnel.length === 0) return '—';
    return r.personnel
      .map((p) => [p.rank_abbreviation, p.surname].filter(Boolean).join(' '))
      .filter(Boolean)
      .join(', ') || '—';
  };

  const viewerLink = (r: SearchRecord) => {
    if (r.collection_id && r.page_number) {
      return `/viewer/${r.collection_id}/${r.page_number}`;
    }
    return '#';
  };

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-parchment">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-parchment/50 border-b border-parchment">
              <th className="px-3 py-2.5 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide">#</th>
              <th onClick={() => toggleSort('date')} className="px-3 py-2.5 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide cursor-pointer hover:text-archive-amber select-none whitespace-nowrap">
                Date<SortIcon k="date" />
              </th>
              <th onClick={() => toggleSort('unit_designation')} className="px-3 py-2.5 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide cursor-pointer hover:text-archive-amber select-none whitespace-nowrap">
                Unit<SortIcon k="unit_designation" />
              </th>
              <th onClick={() => toggleSort('aircraft_type')} className="px-3 py-2.5 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide cursor-pointer hover:text-archive-amber select-none whitespace-nowrap">
                Aircraft<SortIcon k="aircraft_type" />
              </th>
              <th onClick={() => toggleSort('incident_type')} className="px-3 py-2.5 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide cursor-pointer hover:text-archive-amber select-none whitespace-nowrap">
                Incident<SortIcon k="incident_type" />
              </th>
              <th className="px-3 py-2.5 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide">Damage</th>
              <th className="px-3 py-2.5 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide">Personnel</th>
              <th className="px-3 py-2.5 text-left font-body text-xs font-semibold text-slate-ink/50 uppercase tracking-wide">Page</th>
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
                  {r.entry_number ?? ''}
                </td>
                <td className="px-3 py-2 font-body text-xs text-slate-ink/80 whitespace-nowrap">
                  {r.date ?? '—'}
                </td>
                <td className="px-3 py-2 font-body text-xs text-slate-ink font-medium max-w-[10rem] truncate">
                  {r.unit_designation ?? '—'}
                </td>
                <td className="px-3 py-2 font-body text-xs text-slate-ink/80">
                  {r.aircraft_type ?? '—'}
                </td>
                <td className="px-3 py-2 font-body text-xs text-slate-ink/70 italic max-w-[14rem] truncate">
                  {r.incident_type ?? '—'}
                </td>
                <td className="px-3 py-2">
                  <DamageBar level={r.damage_percentage} />
                </td>
                <td className="px-3 py-2 font-body text-xs text-slate-ink/70 max-w-[10rem] truncate">
                  {personnelStr(r)}
                </td>
                <td className="px-3 py-2">
                  <Link
                    to={viewerLink(r)}
                    className="font-mono text-xs text-archive-amber hover:underline"
                  >
                    p.{r.page_number ?? '?'}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="font-body text-xs text-slate-ink/50">
            Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total} results
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="px-3 h-7 rounded border border-parchment font-body text-xs text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              let p: number;
              if (totalPages <= 7) {
                p = i + 1;
              } else if (page <= 4) {
                p = i + 1;
              } else if (page >= totalPages - 3) {
                p = totalPages - 6 + i;
              } else {
                p = page - 3 + i;
              }
              return (
                <button
                  key={p}
                  onClick={() => onPageChange(p)}
                  className={`w-7 h-7 rounded font-mono text-xs transition-colors ${
                    p === page
                      ? 'bg-archive-amber text-white'
                      : 'border border-parchment text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber'
                  }`}
                >
                  {p}
                </button>
              );
            })}
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="px-3 h-7 rounded border border-parchment font-body text-xs text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
