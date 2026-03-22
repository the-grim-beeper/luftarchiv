import { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const BASE_URL = '/api';

const COLORS = [
  '#92400E',
  '#D97706',
  '#F59E0B',
  '#FCD34D',
  '#78350F',
  '#B45309',
  '#FBBF24',
  '#FDE68A',
];

interface OverviewData {
  total_records?: number;
  total_personnel?: number;
  losses_over_time?: Array<{ month: string; count: number }>;
  by_aircraft_type?: Array<{ aircraft_type: string; count: number }>;
  personnel_outcomes?: Array<{ fate: string; count: number }>;
}

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-white border border-parchment rounded-lg p-5">
      <p className="font-body text-sm text-slate-ink/50 mb-1">{label}</p>
      <p className="font-heading text-3xl font-bold text-slate-ink">{value}</p>
    </div>
  );
}

export default function Analytics() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${BASE_URL}/analytics/overview`, {
      headers: { 'Content-Type': 'application/json' },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status} ${r.statusText}`);
        return r.json();
      })
      .then((d) => setData(d))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="font-body text-slate-ink/40 text-sm">Loading analytics…</p>
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

  const lossesData = data?.losses_over_time ?? [];
  const aircraftData = data?.by_aircraft_type ?? [];
  const fatesData = data?.personnel_outcomes ?? [];

  return (
    <div>
      <div className="mb-8">
        <h2 className="font-heading text-3xl font-bold text-slate-ink mb-1">Analytics</h2>
        <p className="font-body text-slate-ink/50 text-sm">
          Aggregate statistics across all extracted archive records.
        </p>
      </div>

      {/* Summary stat cards */}
      <div className="grid grid-cols-2 gap-4 mb-8">
        <StatCard label="Total Records" value={data?.total_records?.toLocaleString() ?? '—'} />
        <StatCard label="Total Personnel" value={data?.total_personnel?.toLocaleString() ?? '—'} />
      </div>

      {/* Losses over time */}
      {lossesData.length > 0 && (
        <div className="bg-white border border-parchment rounded-lg p-5 mb-6">
          <h3 className="font-heading text-lg font-semibold text-slate-ink mb-4">
            Losses Over Time
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={lossesData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F5F0E8" />
              <XAxis
                dataKey="month"
                tick={{ fontFamily: 'Inter, system-ui, sans-serif', fontSize: 11, fill: '#1E293B99' }}
              />
              <YAxis
                tick={{ fontFamily: 'Inter, system-ui, sans-serif', fontSize: 11, fill: '#1E293B99' }}
              />
              <Tooltip
                contentStyle={{
                  fontFamily: 'Inter, system-ui, sans-serif',
                  fontSize: 12,
                  border: '1px solid #F5F0E8',
                  borderRadius: 6,
                }}
              />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#92400E"
                strokeWidth={2}
                dot={{ fill: '#92400E', r: 3 }}
                activeDot={{ r: 5 }}
                name="Losses"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* By aircraft type (horizontal bar) */}
        {aircraftData.length > 0 && (
          <div className="bg-white border border-parchment rounded-lg p-5">
            <h3 className="font-heading text-lg font-semibold text-slate-ink mb-4">
              By Aircraft Type
            </h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart
                data={aircraftData}
                layout="vertical"
                margin={{ top: 4, right: 16, left: 40, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#F5F0E8" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{
                    fontFamily: 'Inter, system-ui, sans-serif',
                    fontSize: 11,
                    fill: '#1E293B99',
                  }}
                />
                <YAxis
                  type="category"
                  dataKey="aircraft_type"
                  tick={{
                    fontFamily: 'Inter, system-ui, sans-serif',
                    fontSize: 11,
                    fill: '#1E293B99',
                  }}
                  width={60}
                />
                <Tooltip
                  contentStyle={{
                    fontFamily: 'Inter, system-ui, sans-serif',
                    fontSize: 12,
                    border: '1px solid #F5F0E8',
                    borderRadius: 6,
                  }}
                />
                <Bar dataKey="count" name="Records" radius={[0, 3, 3, 0]}>
                  {aircraftData.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Personnel outcomes (pie) */}
        {fatesData.length > 0 && (
          <div className="bg-white border border-parchment rounded-lg p-5">
            <h3 className="font-heading text-lg font-semibold text-slate-ink mb-4">
              Personnel Outcomes
            </h3>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={fatesData}
                  dataKey="count"
                  nameKey="fate"
                  cx="50%"
                  cy="50%"
                  outerRadius={85}
                  label={({ name, percent }) =>
                    `${name} ${percent !== undefined ? (percent * 100).toFixed(0) : ''}%`
                  }
                  labelLine={{ stroke: '#1E293B33' }}
                >
                  {fatesData.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    fontFamily: 'Inter, system-ui, sans-serif',
                    fontSize: 12,
                    border: '1px solid #F5F0E8',
                    borderRadius: 6,
                  }}
                />
                <Legend
                  wrapperStyle={{
                    fontFamily: 'Inter, system-ui, sans-serif',
                    fontSize: 12,
                    color: '#1E293B99',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {lossesData.length === 0 && aircraftData.length === 0 && fatesData.length === 0 && (
        <div className="border border-dashed border-parchment rounded-lg py-20 text-center">
          <p className="font-heading text-xl text-slate-ink/30 mb-2">No data yet</p>
          <p className="font-body text-sm text-slate-ink/40">
            Import and extract collections to see analytics.
          </p>
        </div>
      )}
    </div>
  );
}
