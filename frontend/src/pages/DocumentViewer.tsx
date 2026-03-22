import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import ScanViewer from '../components/ScanViewer';
import RecordCard from '../components/RecordCard';
import KnowledgePanel from '../components/KnowledgePanel';

interface PageData {
  id: string;
  page_number: number;
  image_path?: string;
  records?: any[];
  glossary_terms?: any[];
}

interface CollectionData {
  id: string;
  name: string;
  page_count: number;
  pages?: PageData[];
}

export default function DocumentViewer() {
  const { collectionId, pageNumber } = useParams<{
    collectionId: string;
    pageNumber?: string;
  }>();
  const navigate = useNavigate();

  const [collection, setCollection] = useState<CollectionData | null>(null);
  const [currentPage, setCurrentPage] = useState<PageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const pageNum = pageNumber ? parseInt(pageNumber, 10) : 1;

  useEffect(() => {
    if (!collectionId) return;
    setLoading(true);
    api
      .getCollection(collectionId)
      .then((data: CollectionData) => {
        setCollection(data);
        // Find the page matching the current page number
        const page =
          data.pages?.find((p) => p.page_number === pageNum) ??
          data.pages?.[pageNum - 1] ??
          null;
        setCurrentPage(page);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [collectionId, pageNum]);

  const goToPage = (n: number) => {
    navigate(`/viewer/${collectionId}/${n}`);
  };

  const totalPages = collection?.page_count ?? 1;
  const canPrev = pageNum > 1;
  const canNext = pageNum < totalPages;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="font-body text-slate-ink/40 text-sm">Loading document…</p>
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

  const exportUrl = collectionId ? api.exportCsv(collectionId) : null;

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 8rem)' }}>
      {/* Header */}
      <div className="flex items-center gap-4 mb-4 flex-wrap shrink-0">
        <Link
          to="/"
          className="font-body text-sm text-slate-ink/50 hover:text-archive-amber transition-colors flex items-center gap-1"
        >
          ← Collections
        </Link>

        <h2 className="font-heading text-xl font-bold text-slate-ink flex-1 min-w-0 truncate">
          {collection?.name ?? collectionId}
        </h2>

        {/* Page navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => goToPage(pageNum - 1)}
            disabled={!canPrev}
            className="px-3 h-8 rounded border border-parchment font-body text-sm text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            ← Prev
          </button>
          <span className="font-mono text-xs text-slate-ink/50 px-1">
            {pageNum} / {totalPages}
          </span>
          <button
            onClick={() => goToPage(pageNum + 1)}
            disabled={!canNext}
            className="px-3 h-8 rounded border border-parchment font-body text-sm text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Next →
          </button>
        </div>

        {exportUrl && (
          <a
            href={exportUrl}
            download
            className="px-3 h-8 flex items-center rounded border border-archive-amber text-archive-amber font-body text-sm hover:bg-archive-amber hover:text-white transition-colors"
          >
            Export CSV
          </a>
        )}
      </div>

      {/* Split pane */}
      <div className="flex gap-4 flex-1 overflow-hidden">
        {/* Left: scan viewer */}
        <div className="flex-1 overflow-hidden border border-parchment rounded-lg bg-white flex flex-col">
          <ScanViewer imagePath={currentPage?.image_path ?? null} />
        </div>

        {/* Right: record cards */}
        <div className="w-96 shrink-0 overflow-y-auto">
          {!currentPage?.records || currentPage.records.length === 0 ? (
            <div className="border border-dashed border-parchment rounded-lg p-6 text-center">
              <p className="font-body text-sm text-slate-ink/40">
                No records extracted for this page yet.
              </p>
            </div>
          ) : (
            currentPage.records.map((r: any) => (
              <RecordCard key={r.id} record={r} />
            ))
          )}
        </div>
      </div>

      {/* Bottom: knowledge panel */}
      <div className="shrink-0 mt-2 border border-parchment rounded-lg overflow-hidden">
        <KnowledgePanel terms={currentPage?.glossary_terms ?? []} />
      </div>
    </div>
  );
}
