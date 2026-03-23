import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import ScanViewer from '../components/ScanViewer';
import RecordCard from '../components/RecordCard';
import KnowledgePanel from '../components/KnowledgePanel';

interface CollectionData {
  id: string;
  name: string;
  page_count: number;
}

interface PageRecordsData {
  page: { id: string; image_path: string; page_number: number };
  records: any[];
}

export default function DocumentViewer() {
  const { collectionId, pageNumber } = useParams<{
    collectionId: string;
    pageNumber?: string;
  }>();
  const navigate = useNavigate();

  const [collection, setCollection] = useState<CollectionData | null>(null);
  const [pageData, setPageData] = useState<PageRecordsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const pageNum = pageNumber ? parseInt(pageNumber, 10) : 1;

  // Fetch collection info
  useEffect(() => {
    if (!collectionId) return;
    api.getCollection(collectionId).then(setCollection).catch((e: Error) => setError(e.message));
  }, [collectionId]);

  // Fetch page records
  useEffect(() => {
    if (!collectionId) return;
    setLoading(true);
    setPageData(null);
    fetch(`/api/collections/${collectionId}/pages/${pageNum}/records`)
      .then((r) => {
        if (!r.ok) throw new Error(`Page not found: ${r.status}`);
        return r.json();
      })
      .then((data: PageRecordsData) => {
        setPageData(data);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [collectionId, pageNum]);

  const goToPage = (n: number) => {
    navigate(`/viewer/${collectionId}/${n}`);
  };

  const [extracting, setExtracting] = useState(false);
  const [extractJob, setExtractJob] = useState<{
    status: string;
    processed_pages: number;
    total_pages: number;
    error_message?: string;
  } | null>(null);

  // Check for active extraction jobs on mount and poll while running
  useEffect(() => {
    if (!collectionId) return;
    let interval: ReturnType<typeof setInterval> | null = null;

    const checkJobs = async () => {
      try {
        const res = await fetch(`/api/collections/${collectionId}/jobs`);
        const jobs = await res.json();
        const active = jobs.find((j: any) => j.stage === 'claude' && j.status === 'running');
        const latest = jobs.find((j: any) => j.stage === 'claude');
        if (active) {
          setExtractJob(active);
          setExtracting(true);
          if (!interval) {
            interval = setInterval(checkJobs, 3000);
          }
        } else if (latest && latest.status === 'completed' && extracting) {
          setExtractJob(latest);
          setExtracting(false);
          if (interval) clearInterval(interval);
          // Reload page data to show new records
          fetch(`/api/collections/${collectionId}/pages/${pageNum}/records`)
            .then((r) => r.json())
            .then(setPageData);
        } else if (latest && latest.status === 'failed') {
          setExtractJob(latest);
          setExtracting(false);
          if (interval) clearInterval(interval);
        } else {
          setExtractJob(null);
        }
      } catch {}
    };

    checkJobs();
    return () => { if (interval) clearInterval(interval); };
  }, [collectionId, extracting]);

  const totalPages = collection?.page_count ?? 1;
  const canPrev = pageNum > 1;
  const canNext = pageNum < totalPages;

  if (loading && !collection) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="font-body text-slate-ink/40 text-sm">Loading document...</p>
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

  const startExtraction = async () => {
    if (!collectionId) return;
    setExtracting(true);
    try {
      await api.startExtraction(collectionId, 'claude');
      setExtractJob({ status: 'running', processed_pages: 0, total_pages: totalPages });
    } catch (e: any) {
      setExtracting(false);
      setExtractJob({ status: 'failed', processed_pages: 0, total_pages: 0, error_message: e.message });
    }
  };

  const reExtract = async () => {
    if (!collectionId) return;
    if (!confirm('This will delete all extracted records for this collection and re-extract with the currently configured model. Continue?')) return;
    setExtracting(true);
    try {
      await fetch(`/api/collections/${collectionId}/reset-extraction`, { method: 'POST' });
      await api.startExtraction(collectionId, 'claude');
      setExtractJob({ status: 'running', processed_pages: 0, total_pages: totalPages });
      setPageData(null);
    } catch (e: any) {
      setExtracting(false);
      setExtractJob({ status: 'failed', processed_pages: 0, total_pages: 0, error_message: e.message });
    }
  };

  const exportUrl = collectionId ? api.exportCsv(collectionId) : null;
  const imagePath = pageData?.page?.image_path ?? null;
  const records = pageData?.records ?? [];

  // Extract terms from records for glossary panel
  const terms = [
    ...new Set(
      records.flatMap((r: any) => [
        r.incident_type,
        r.unit_designation,
        ...(r.personnel ?? []).map((p: any) => p.rank_abbreviation),
      ].filter(Boolean))
    ),
  ];

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 8rem)' }}>
      {/* Header */}
      <div className="flex items-center gap-4 mb-4 flex-wrap shrink-0">
        <Link
          to="/"
          className="font-body text-sm text-slate-ink/50 hover:text-archive-amber transition-colors"
        >
          ← Collections
        </Link>

        <h2 className="font-heading text-xl font-bold text-slate-ink flex-1 min-w-0 truncate">
          {collection?.name ?? collectionId}
        </h2>

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

        {records.length === 0 && !extracting && !extractJob && (
          <button
            onClick={startExtraction}
            className="px-3 h-8 flex items-center rounded bg-trust-ai text-white font-body text-sm hover:bg-indigo-600 transition-colors"
          >
            Extract with Claude
          </button>
        )}
        {records.length > 0 && !extracting && (
          <button
            onClick={reExtract}
            className="px-3 h-8 flex items-center rounded border border-slate-ink/20 text-slate-ink/50 font-body text-xs hover:border-red-300 hover:text-red-600 transition-colors"
            title="Delete all records and re-extract with the currently configured model"
          >
            Re-extract
          </button>
        )}
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

      {/* Extraction progress banner */}
      {extractJob && extractJob.status === 'running' && (
        <div className="mb-3 p-3 bg-indigo-50 border border-indigo-200 rounded-lg shrink-0">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-body text-sm text-indigo-700">
              Extracting records with Claude...
            </span>
            <span className="font-mono text-xs text-indigo-600">
              {extractJob.processed_pages} / {extractJob.total_pages} pages
            </span>
          </div>
          <div className="h-2 bg-indigo-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all duration-1000"
              style={{
                width: `${extractJob.total_pages > 0
                  ? (extractJob.processed_pages / extractJob.total_pages) * 100
                  : 0}%`,
              }}
            />
          </div>
          <p className="font-body text-xs text-indigo-500 mt-1.5">
            Records appear as each page is processed. This page will update automatically.
          </p>
        </div>
      )}
      {extractJob && extractJob.status === 'failed' && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg shrink-0">
          <span className="font-body text-sm text-red-700">
            Extraction failed: {extractJob.error_message || 'Unknown error'}
          </span>
          <button
            onClick={startExtraction}
            className="ml-3 px-2 h-6 rounded bg-red-600 text-white font-body text-xs hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}
      {extractJob && extractJob.status === 'completed' && extractJob.processed_pages > 0 && (
        <div className="mb-3 p-2 bg-emerald-50 border border-emerald-200 rounded-lg shrink-0 flex items-center gap-2">
          <span className="font-body text-sm text-emerald-700">
            Extraction complete — {extractJob.processed_pages} pages processed.
          </span>
        </div>
      )}

      {/* Split pane */}
      <div className="flex gap-4 flex-1 overflow-hidden">
        {/* Left: scan viewer */}
        <div className="flex-1 overflow-hidden border border-parchment rounded-lg bg-white flex flex-col">
          <ScanViewer imagePath={imagePath} />
        </div>

        {/* Right: record cards */}
        <div className="w-96 shrink-0 overflow-y-auto">
          {records.length === 0 ? (
            <div className="border border-dashed border-parchment rounded-lg p-6 text-center">
              <p className="font-body text-sm text-slate-ink/40">
                {loading ? 'Loading...' : 'No records extracted for this page yet.'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {records.map((r: any) => (
                <RecordCard key={r.id} record={r} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom: knowledge panel */}
      <div className="shrink-0 mt-2 border border-parchment rounded-lg overflow-hidden">
        <KnowledgePanel terms={terms} />
      </div>
    </div>
  );
}
