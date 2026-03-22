import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

interface Collection {
  id: string;
  name: string;
  source_reference: string;
  description?: string;
  page_count: number;
  status: 'complete' | 'processing' | 'pending';
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    complete: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    processing: 'bg-amber-50 text-amber-700 border border-amber-200',
    pending: 'bg-slate-50 text-slate-500 border border-slate-200',
  };
  const labels: Record<string, string> = {
    complete: 'Complete',
    processing: 'Processing',
    pending: 'Pending',
  };
  const cls = styles[status] ?? styles.pending;
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-body font-medium ${cls}`}>
      {labels[status] ?? status}
    </span>
  );
}

function CollectionCard({ collection }: { collection: Collection }) {
  return (
    <Link
      to={`/viewer/${collection.id}`}
      className="block bg-white border border-parchment rounded-lg p-5 hover:border-archive-amber hover:shadow-sm transition-all group"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="font-heading text-lg font-semibold text-slate-ink group-hover:text-archive-amber transition-colors leading-tight">
          {collection.name}
        </h3>
        <StatusBadge status={collection.status} />
      </div>
      <p className="font-mono text-xs text-slate-ink/50 mb-3 tracking-tight">
        {collection.source_reference}
      </p>
      {collection.description && (
        <p className="font-body text-sm text-slate-ink/70 mb-4 line-clamp-2">
          {collection.description}
        </p>
      )}
      <div className="flex items-center gap-1 text-xs font-body text-slate-ink/40">
        <span className="font-semibold text-slate-ink/60">{collection.page_count}</span>
        <span>{collection.page_count === 1 ? 'page' : 'pages'}</span>
      </div>
    </Link>
  );
}

export default function Collections() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listCollections()
      .then((data) => setCollections(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="font-body text-slate-ink/40 text-sm">Loading collections…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="font-body text-red-600 text-sm">Error: {error}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="font-heading text-3xl font-bold text-slate-ink mb-1">Collections</h2>
        <p className="font-body text-slate-ink/50 text-sm">
          Digitised archive documents available for extraction and search.
        </p>
      </div>

      {collections.length === 0 ? (
        <div className="border border-dashed border-parchment rounded-lg py-20 text-center">
          <p className="font-heading text-xl text-slate-ink/30 mb-2">No collections yet</p>
          <p className="font-body text-sm text-slate-ink/40">
            Import a folder of scanned pages to get started.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {collections.map((c) => (
            <CollectionCard key={c.id} collection={c} />
          ))}
        </div>
      )}
    </div>
  );
}
