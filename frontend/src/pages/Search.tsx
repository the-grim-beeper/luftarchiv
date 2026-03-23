import { useState } from 'react';
import { api } from '../api/client';
import SearchBar from '../components/SearchBar';
import RecordTable from '../components/RecordTable';

const PAGE_SIZE = 50;

export default function Search() {
  const [results, setResults] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [lastFilters, setLastFilters] = useState<any>(null);

  const doSearch = (filters: any, page: number = 1) => {
    setLoading(true);
    setError(null);
    const searchPayload = {
      ...filters,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    };
    api
      .search(searchPayload)
      .then((data) => {
        setResults(data.records ?? data.results ?? []);
        setTotal(data.total ?? 0);
        setSearched(true);
        setCurrentPage(page);
        setLastFilters(filters);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  const handleSearch = (filters: any) => doSearch(filters, 1);
  const handlePageChange = (page: number) => {
    if (lastFilters) doSearch(lastFilters, page);
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="font-heading text-3xl font-bold text-slate-ink mb-1">Search</h2>
        <p className="font-body text-slate-ink/50 text-sm">
          Search across all extracted records. Use filters for precise queries.
        </p>
      </div>

      <SearchBar onSearch={handleSearch} loading={loading} />

      {error && (
        <p className="font-body text-sm text-red-600 mb-4">Error: {error}</p>
      )}

      {searched && !loading && (
        <div className="mb-3">
          <span className="font-body text-sm text-slate-ink/50">
            {total === 0 ? 'No results' : `${total} result${total === 1 ? '' : 's'}`}
          </span>
        </div>
      )}

      {searched && (
        <RecordTable
          records={results}
          total={total}
          page={currentPage}
          pageSize={PAGE_SIZE}
          onPageChange={handlePageChange}
        />
      )}

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
