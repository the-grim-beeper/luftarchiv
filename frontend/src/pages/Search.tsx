import { useState } from 'react';
import { api } from '../api/client';
import SearchBar from '../components/SearchBar';
import RecordTable from '../components/RecordTable';

export default function Search() {
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = (filters: any) => {
    setLoading(true);
    setError(null);
    api
      .search(filters)
      .then((data) => {
        setResults(Array.isArray(data) ? data : data.records ?? data.results ?? []);
        setSearched(true);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="font-heading text-3xl font-bold text-slate-ink mb-1">Search</h2>
        <p className="font-body text-slate-ink/50 text-sm">
          Full-text search across all extracted records.
        </p>
      </div>

      <SearchBar onSearch={handleSearch} loading={loading} />

      {error && (
        <p className="font-body text-sm text-red-600 mb-4">Error: {error}</p>
      )}

      {searched && !loading && (
        <div className="mb-3 flex items-center gap-2">
          <span className="font-body text-sm text-slate-ink/50">
            {results.length === 0
              ? 'No results'
              : `${results.length} result${results.length === 1 ? '' : 's'}`}
          </span>
        </div>
      )}

      {searched && <RecordTable records={results} />}

      {!searched && !loading && (
        <div className="border border-dashed border-parchment rounded-lg py-20 text-center">
          <p className="font-heading text-xl text-slate-ink/30 mb-2">Enter a search query</p>
          <p className="font-body text-sm text-slate-ink/40">
            Search by unit, aircraft type, incident, personnel name, or free text.
          </p>
        </div>
      )}
    </div>
  );
}
