interface Personnel {
  name?: string;
  rank?: string;
  fate?: 'killed' | 'wounded' | 'missing' | 'uninjured' | string;
}

interface ArchiveRecord {
  id: string;
  entry_number?: string | number;
  date?: string;
  unit?: string;
  aircraft?: string;
  werknummer?: string;
  incident_type?: string;
  damage_level?: number; // 0-100
  personnel?: Personnel[];
}

interface RecordCardProps {
  record: ArchiveRecord;
}

const FATE_STYLES: Record<string, string> = {
  killed: 'bg-red-50 text-red-700 border border-red-200',
  wounded: 'bg-amber-50 text-amber-700 border border-amber-200',
  missing: 'bg-purple-50 text-purple-700 border border-purple-200',
  uninjured: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
};

function FateBadge({ fate }: { fate: string }) {
  const cls = FATE_STYLES[fate] ?? 'bg-slate-50 text-slate-500 border border-slate-200';
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-body font-medium ${cls}`}>
      {fate}
    </span>
  );
}

function DamageBar({ level }: { level: number }) {
  const pct = Math.min(100, Math.max(0, level));
  const color =
    pct >= 75 ? 'bg-red-500' : pct >= 40 ? 'bg-amber-500' : 'bg-emerald-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-parchment rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-slate-ink/50 w-8 text-right">{pct}%</span>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string | number | null }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex gap-2">
      <span className="font-body text-xs text-slate-ink/40 w-24 shrink-0">{label}</span>
      <span className="font-body text-xs text-slate-ink/80 break-all">{value}</span>
    </div>
  );
}

export default function RecordCard({ record }: RecordCardProps) {
  return (
    <div className="bg-white border border-parchment rounded-lg p-4 mb-3">
      <div className="flex items-center gap-2 mb-3">
        <span className="font-mono text-xs text-slate-ink/40">#</span>
        <span className="font-heading text-base font-semibold text-slate-ink">
          {record.entry_number ?? '—'}
        </span>
        {record.incident_type && (
          <span className="ml-auto font-body text-xs text-slate-ink/50 border border-parchment rounded px-2 py-0.5">
            {record.incident_type}
          </span>
        )}
      </div>

      <div className="space-y-1.5 mb-3">
        <Row label="Date" value={record.date} />
        <Row label="Unit" value={record.unit} />
        <Row label="Aircraft" value={record.aircraft} />
        <Row label="Werknummer" value={record.werknummer} />
      </div>

      {record.damage_level !== undefined && record.damage_level !== null && (
        <div className="mb-3">
          <p className="font-body text-xs text-slate-ink/40 mb-1">Damage</p>
          <DamageBar level={record.damage_level} />
        </div>
      )}

      {record.personnel && record.personnel.length > 0 && (
        <div>
          <p className="font-body text-xs text-slate-ink/40 mb-1.5">Personnel</p>
          <div className="space-y-1.5">
            {record.personnel.map((p, i) => (
              <div key={i} className="flex items-center gap-2 flex-wrap">
                {p.rank && (
                  <span className="font-mono text-xs text-slate-ink/50">{p.rank}</span>
                )}
                {p.name && (
                  <span className="font-body text-xs text-slate-ink/80">{p.name}</span>
                )}
                {p.fate && <FateBadge fate={p.fate} />}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
