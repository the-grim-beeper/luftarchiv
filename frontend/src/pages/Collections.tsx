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
    importing: 'bg-blue-50 text-blue-700 border border-blue-200 animate-pulse',
    pending: 'bg-slate-50 text-slate-500 border border-slate-200',
  };
  const labels: Record<string, string> = {
    complete: 'Complete',
    processing: 'Processing',
    importing: 'Importing...',
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

interface BrowseEntry {
  name: string;
  path: string;
  type: string;
  image_count: number;
}

function FolderBrowser({
  onSelect,
  onCancel,
}: {
  onSelect: (path: string) => void;
  onCancel: () => void;
}) {
  const [currentPath, setCurrentPath] = useState('~');
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [entries, setEntries] = useState<BrowseEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const browse = (path: string) => {
    setLoading(true);
    fetch(`/api/import/browse?path=${encodeURIComponent(path)}`)
      .then((r) => {
        if (!r.ok) throw new Error('Could not browse path');
        return r.json();
      })
      .then((data) => {
        setCurrentPath(data.current);
        setParentPath(data.parent);
        setEntries(data.entries);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { browse('~'); }, []);

  return (
    <div className="space-y-3">
      {/* Current path */}
      <div className="flex items-center gap-2">
        {parentPath && (
          <button
            onClick={() => browse(parentPath)}
            className="px-2 h-7 rounded border border-parchment text-xs font-mono text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors"
          >
            ← Up
          </button>
        )}
        <span className="font-mono text-xs text-slate-ink/50 truncate flex-1">{currentPath}</span>
        <button
          onClick={() => onSelect(currentPath)}
          className="px-3 h-7 rounded bg-archive-amber text-white text-xs font-body hover:bg-archive-amber-light transition-colors"
        >
          Select this folder
        </button>
      </div>

      {/* Folder list */}
      <div className="border border-parchment rounded-lg max-h-56 overflow-y-auto bg-ivory/50">
        {loading ? (
          <p className="p-3 text-xs text-slate-ink/40 font-body">Loading...</p>
        ) : entries.length === 0 ? (
          <p className="p-3 text-xs text-slate-ink/40 font-body">No subfolders</p>
        ) : (
          entries.map((e) => (
            <button
              key={e.path}
              onClick={() => browse(e.path)}
              onDoubleClick={() => {
                if (e.image_count > 0) onSelect(e.path);
              }}
              className="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-parchment/50 transition-colors border-b border-parchment/50 last:border-b-0"
            >
              <span className="text-archive-amber text-sm">&#128193;</span>
              <span className="font-body text-sm text-slate-ink flex-1 truncate">{e.name}</span>
              {e.image_count > 0 && (
                <span className="text-xs font-mono text-trust-verified bg-emerald-50 px-1.5 py-0.5 rounded">
                  {e.image_count} images
                </span>
              )}
            </button>
          ))
        )}
      </div>
      <p className="font-body text-xs text-slate-ink/40">
        Click a folder to open it. Double-click a folder with images to select it.
      </p>
    </div>
  );
}

function ImportDialog({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const [folderPath, setFolderPath] = useState('');
  const [name, setName] = useState('');
  const [sourceRef, setSourceRef] = useState('');
  const [description, setDescription] = useState('');
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showBrowser, setShowBrowser] = useState(true);

  const handleSelectFolder = (path: string) => {
    setFolderPath(path);
    // Auto-fill name from folder name
    const folderName = path.split('/').pop() || '';
    if (!name) setName(folderName.replace(/_/g, ' '));
    setShowBrowser(false);
  };

  const [importProgress, setImportProgress] = useState<{ pages_imported: number; total_pages: number } | null>(null);

  const handleImport = async () => {
    if (!folderPath || !name) return;
    setImporting(true);
    setError(null);
    try {
      const collection = await api.importFolder({
        folder_path: folderPath,
        name,
        source_reference: sourceRef || undefined,
        description: description || undefined,
        document_type: 'loss_report',
      });

      // Poll for progress
      const collectionId = collection.id;
      const poll = setInterval(async () => {
        try {
          const res = await fetch(`/api/import/progress/${collectionId}`);
          const data = await res.json();
          setImportProgress({ pages_imported: data.pages_imported, total_pages: data.total_pages });
          if (data.done) {
            clearInterval(poll);
            onImported();
          }
        } catch {
          clearInterval(poll);
        }
      }, 1500);
    } catch (e: any) {
      setError(e.message);
      setImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-ink/30 backdrop-blur-sm">
      <div className="bg-white rounded-xl border border-parchment shadow-lg w-full max-w-2xl mx-4 p-6">
        <h3 className="font-heading text-xl font-bold text-slate-ink mb-4">Import Collection</h3>

        {showBrowser ? (
          <>
            <p className="font-body text-sm text-slate-ink/50 mb-4">
              Browse to a folder containing scanned document images (JPG, PNG, TIFF).
            </p>
            <FolderBrowser
              onSelect={handleSelectFolder}
              onCancel={onClose}
            />
            <div className="flex justify-between mt-5 pt-4 border-t border-parchment">
              <button
                onClick={onClose}
                className="px-4 h-9 rounded-lg border border-parchment font-body text-sm text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors"
              >
                Cancel
              </button>
              <div className="flex items-center gap-3">
                <span className="font-body text-xs text-slate-ink/40">Or enter path manually:</span>
                <button
                  onClick={() => setShowBrowser(false)}
                  className="px-3 h-8 rounded border border-parchment font-body text-xs text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors"
                >
                  Type path
                </button>
              </div>
            </div>
          </>
        ) : (
          <>
            <p className="font-body text-sm text-slate-ink/50 mb-5">
              Configure the collection details.
            </p>
            <div className="space-y-4">
              <div>
                <label className="block font-body text-xs text-slate-ink/60 mb-1">
                  Folder path <span className="text-red-400">*</span>
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={folderPath}
                    onChange={(e) => setFolderPath(e.target.value)}
                    placeholder="/Users/you/Desktop/RL 2-III_1190"
                    className="flex-1 h-9 px-3 border border-parchment rounded-lg font-mono text-sm text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
                  />
                  <button
                    onClick={() => setShowBrowser(true)}
                    className="px-3 h-9 rounded-lg border border-parchment font-body text-xs text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors"
                  >
                    Browse
                  </button>
                </div>
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

            {importProgress && (
              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-body text-sm text-blue-700">
                    Importing pages...
                  </span>
                  <span className="font-mono text-xs text-blue-600">
                    {importProgress.pages_imported} / {importProgress.total_pages}
                  </span>
                </div>
                <div className="h-2 bg-blue-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all duration-500"
                    style={{
                      width: `${importProgress.total_pages > 0
                        ? (importProgress.pages_imported / importProgress.total_pages) * 100
                        : 0}%`,
                    }}
                  />
                </div>
              </div>
            )}

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
          </>
        )}
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
