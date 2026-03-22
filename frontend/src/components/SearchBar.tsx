import { useState } from 'react';

interface Filters {
  query: string;
  unit?: string;
  aircraft_type?: string;
  incident_type?: string;
  personnel_name?: string;
  date_from?: string;
  date_to?: string;
}

interface SearchBarProps {
  onSearch: (filters: Filters) => void;
  loading?: boolean;
}

export default function SearchBar({ onSearch, loading }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Omit<Filters, 'query'>>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch({ query, ...filters });
  };

  const setFilter = (key: keyof typeof filters, value: string) => {
    setFilters((f) => ({ ...f, [key]: value || undefined }));
  };

  return (
    <form onSubmit={handleSubmit} className="mb-6">
      <div className="flex gap-2 mb-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search records — unit, aircraft, personnel, notes…"
          className="flex-1 h-10 px-4 border border-parchment rounded-lg font-body text-sm text-slate-ink placeholder:text-slate-ink/30 bg-white focus:outline-none focus:border-archive-amber transition-colors"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-5 h-10 bg-archive-amber text-white font-body text-sm rounded-lg hover:bg-archive-amber-light transition-colors disabled:opacity-50"
        >
          {loading ? 'Searching…' : 'Search'}
        </button>
        <button
          type="button"
          onClick={() => setShowFilters((s) => !s)}
          className={`px-3 h-10 rounded-lg border font-body text-sm transition-colors ${
            showFilters
              ? 'border-archive-amber text-archive-amber bg-amber-50'
              : 'border-parchment text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber'
          }`}
        >
          Filters
        </button>
      </div>

      {showFilters && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 p-4 bg-white border border-parchment rounded-lg">
          {(
            [
              ['unit', 'Unit'],
              ['aircraft_type', 'Aircraft type'],
              ['incident_type', 'Incident type'],
              ['personnel_name', 'Personnel name'],
            ] as [keyof typeof filters, string][]
          ).map(([key, label]) => (
            <div key={key}>
              <label className="block font-body text-xs text-slate-ink/50 mb-1">{label}</label>
              <input
                type="text"
                value={filters[key] ?? ''}
                onChange={(e) => setFilter(key, e.target.value)}
                className="w-full h-8 px-3 border border-parchment rounded font-body text-xs text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
              />
            </div>
          ))}
          <div>
            <label className="block font-body text-xs text-slate-ink/50 mb-1">Date from</label>
            <input
              type="date"
              value={filters.date_from ?? ''}
              onChange={(e) => setFilter('date_from', e.target.value)}
              className="w-full h-8 px-3 border border-parchment rounded font-body text-xs text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
            />
          </div>
          <div>
            <label className="block font-body text-xs text-slate-ink/50 mb-1">Date to</label>
            <input
              type="date"
              value={filters.date_to ?? ''}
              onChange={(e) => setFilter('date_to', e.target.value)}
              className="w-full h-8 px-3 border border-parchment rounded font-body text-xs text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
            />
          </div>
        </div>
      )}
    </form>
  );
}
