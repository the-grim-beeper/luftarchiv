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

function ImportDialog({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const [folderPath, setFolderPath] = useState('');
  const [name, setName] = useState('');
  const [sourceRef, setSourceRef] = useState('');
  const [description, setDescription] = useState('');
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleImport = async () => {
    if (!folderPath || !name) return;
    setImporting(true);
    setError(null);
    try {
      await api.importFolder({
        folder_path: folderPath,
        name,
        source_reference: sourceRef || undefined,
        description: description || undefined,
        document_type: 'loss_report',
      });
      onImported();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-ink/30 backdrop-blur-sm">
      <div className="bg-white rounded-xl border border-parchment shadow-lg w-full max-w-lg mx-4 p-6">
        <h3 className="font-heading text-xl font-bold text-slate-ink mb-4">Import Collection</h3>
        <p className="font-body text-sm text-slate-ink/50 mb-5">
          Point to a folder of scanned document images (JPG, PNG, TIFF).
        </p>

        <div className="space-y-4">
          <div>
            <label className="block font-body text-xs text-slate-ink/60 mb-1">
              Folder path <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              placeholder="/Users/you/Desktop/RL 2-III_1190"
              className="w-full h-9 px-3 border border-parchment rounded-lg font-mono text-sm text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
            />
          </div>
          <div>
            <label className="block font-body text-xs text-slate-ink/60 mb-1">
              Collection name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="RL 2-III/1190"
              className="w-full h-9 px-3 border border-parchment rounded-lg font-body text-sm text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
            />
          </div>
          <div>
            <label className="block font-body text-xs text-slate-ink/60 mb-1">
              Source reference
            </label>
            <input
              type="text"
              value={sourceRef}
              onChange={(e) => setSourceRef(e.target.value)}
              placeholder="RL_2_III_1190"
              className="w-full h-9 px-3 border border-parchment rounded-lg font-mono text-sm text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
            />
          </div>
          <div>
            <label className="block font-body text-xs text-slate-ink/60 mb-1">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Aircraft accidents and losses at front units"
              className="w-full h-9 px-3 border border-parchment rounded-lg font-body text-sm text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
            />
          </div>
        </div>

        {error && <p className="font-body text-sm text-red-600 mt-3">{error}</p>}

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            disabled={importing}
            className="px-4 h-9 rounded-lg border border-parchment font-body text-sm text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleImport}
            disabled={importing || !folderPath || !name}
            className="px-5 h-9 rounded-lg bg-archive-amber text-white font-body text-sm hover:bg-archive-amber-light transition-colors disabled:opacity-50"
          >
            {importing ? 'Importing...' : 'Import'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Collections() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);

  const loadCollections = () => {
    setLoading(true);
    api
      .listCollections()
      .then((data) => setCollections(data.collections ?? data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(loadCollections, []);

  if (loading && collections.length === 0) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="font-body text-slate-ink/40 text-sm">Loading collections...</p>
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
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="font-heading text-3xl font-bold text-slate-ink mb-1">Collections</h2>
          <p className="font-body text-slate-ink/50 text-sm">
            Digitised archive documents available for extraction and search.
          </p>
        </div>
        <button
          onClick={() => setShowImport(true)}
          className="px-4 h-9 rounded-lg bg-archive-amber text-white font-body text-sm hover:bg-archive-amber-light transition-colors"
        >
          + Import folder
        </button>
      </div>

      {collections.length === 0 ? (
        <div className="border border-dashed border-parchment rounded-lg py-20 text-center">
          <p className="font-heading text-xl text-slate-ink/30 mb-2">No collections yet</p>
          <p className="font-body text-sm text-slate-ink/40 mb-4">
            Import a folder of scanned pages to get started.
          </p>
          <button
            onClick={() => setShowImport(true)}
            className="px-5 h-9 rounded-lg bg-archive-amber text-white font-body text-sm hover:bg-archive-amber-light transition-colors"
          >
            + Import folder
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {collections.map((c) => (
            <CollectionCard key={c.id} collection={c} />
          ))}
        </div>
      )}

      {showImport && (
        <ImportDialog
          onClose={() => setShowImport(false)}
          onImported={() => {
            setShowImport(false);
            loadCollections();
          }}
        />
      )}
    </div>
  );
}
