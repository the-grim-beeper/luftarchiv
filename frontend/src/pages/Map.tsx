import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface GeoLocation {
  location: string;
  lat: number;
  lng: number;
  resolved_name: string;
  country: string;
  record_count: number;
}

interface GeoStats {
  unique_locations: number;
  geocoded: number;
  records_with_location: number;
}

export default function MapPage() {
  const [locations, setLocations] = useState<GeoLocation[]>([]);
  const [stats, setStats] = useState<GeoStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [geocoding, setGeocoding] = useState(false);
  const [geocodeResult, setGeocodeResult] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      fetch('/api/geocode/locations').then((r) => r.json()),
      fetch('/api/geocode/stats').then((r) => r.json()),
    ])
      .then(([locData, statsData]) => {
        setLocations(locData.locations ?? []);
        setStats(statsData);
      })
      .finally(() => setLoading(false));
  };

  useEffect(loadData, []);

  const runGeocoding = async () => {
    setGeocoding(true);
    setGeocodeResult(null);
    try {
      const res = await fetch('/api/geocode/run?batch_size=150', { method: 'POST' });
      const data = await res.json();
      if (data.detail) {
        setGeocodeResult(`Error: ${data.detail}`);
      } else {
        setGeocodeResult(`Geocoded ${data.geocoded} locations.`);
        loadData();
      }
    } catch (e: any) {
      setGeocodeResult(`Error: ${e.message}`);
    } finally {
      setGeocoding(false);
    }
  };

  // Compute marker radius based on record count
  const maxCount = Math.max(...locations.map((l) => l.record_count), 1);
  const getRadius = (count: number) => Math.max(4, Math.min(20, (count / maxCount) * 20 + 4));
  const getColor = (count: number) => {
    if (count >= 15) return '#DC2626'; // red
    if (count >= 8) return '#D97706'; // amber
    return '#92400E'; // archive amber
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-heading text-3xl font-bold text-slate-ink mb-1">Crash Site Map</h2>
          <p className="font-body text-slate-ink/50 text-sm">
            Geographic visualization of aircraft loss locations.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {stats && (
            <span className="font-body text-xs text-slate-ink/50">
              {stats.geocoded} / {stats.unique_locations} locations geocoded
            </span>
          )}
          <button
            onClick={runGeocoding}
            disabled={geocoding}
            className="px-4 h-9 rounded-lg bg-archive-amber text-white font-body text-sm hover:bg-archive-amber-light transition-colors disabled:opacity-50"
          >
            {geocoding ? 'Geocoding...' : locations.length === 0 ? 'Geocode Locations' : 'Geocode More'}
          </button>
        </div>
      </div>

      {geocodeResult && (
        <div className={`mb-4 p-3 rounded-lg border font-body text-sm ${
          geocodeResult.startsWith('Error')
            ? 'bg-red-50 border-red-200 text-red-700'
            : 'bg-emerald-50 border-emerald-200 text-emerald-700'
        }`}>
          {geocodeResult}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <p className="font-body text-slate-ink/40 text-sm">Loading map data...</p>
        </div>
      ) : locations.length === 0 ? (
        <div className="border border-dashed border-parchment rounded-lg py-20 text-center">
          <p className="font-heading text-xl text-slate-ink/30 mb-2">No locations geocoded yet</p>
          <p className="font-body text-sm text-slate-ink/40 mb-4">
            Click "Geocode Locations" to resolve crash site names to map coordinates using AI.
          </p>
        </div>
      ) : (
        <>
          {/* Legend */}
          <div className="flex items-center gap-6 mb-3 px-1">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#92400E]" />
              <span className="font-body text-xs text-slate-ink/50">1-7 losses</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#D97706]" />
              <span className="font-body text-xs text-slate-ink/50">8-14 losses</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#DC2626]" />
              <span className="font-body text-xs text-slate-ink/50">15+ losses</span>
            </div>
            <span className="font-body text-xs text-slate-ink/40 ml-auto">
              {locations.length} locations, {locations.reduce((s, l) => s + l.record_count, 0)} records mapped
            </span>
          </div>

          {/* Map */}
          <div className="rounded-lg overflow-hidden border border-parchment" style={{ height: '600px' }}>
            <MapContainer
              center={[48, 20]}
              zoom={4}
              style={{ height: '100%', width: '100%' }}
              scrollWheelZoom={true}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {locations.map((loc) => (
                <CircleMarker
                  key={loc.location}
                  center={[loc.lat, loc.lng]}
                  radius={getRadius(loc.record_count)}
                  pathOptions={{
                    color: getColor(loc.record_count),
                    fillColor: getColor(loc.record_count),
                    fillOpacity: 0.6,
                    weight: 1,
                  }}
                >
                  <Popup>
                    <div className="font-body text-sm">
                      <p className="font-semibold text-slate-ink">{loc.resolved_name || loc.location}</p>
                      {loc.resolved_name && loc.resolved_name !== loc.location && (
                        <p className="text-xs text-slate-ink/50">Original: {loc.location}</p>
                      )}
                      <p className="text-xs text-slate-ink/70 mt-1">
                        {loc.record_count} loss record{loc.record_count !== 1 ? 's' : ''}
                      </p>
                      {loc.country && (
                        <p className="text-xs text-slate-ink/50">{loc.country}</p>
                      )}
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
        </>
      )}
    </div>
  );
}
