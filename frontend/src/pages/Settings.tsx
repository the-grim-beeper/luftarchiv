import { useEffect, useState } from 'react';

interface SettingsData {
  provider: string;
  api_key_set: boolean;
  ollama_url: string;
  model_name: string;
  effective_model: string;
  kraken_enabled: boolean;
  kraken_available: boolean;
}

interface TestResult {
  status: string;
  message: string;
  models?: string[];
}

export default function Settings() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState(false);

  // Form state
  const [provider, setProvider] = useState('claude');
  const [apiKey, setApiKey] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [modelName, setModelName] = useState('');
  const [krakenEnabled, setKrakenEnabled] = useState(false);

  useEffect(() => {
    fetch('/api/settings')
      .then((r) => r.json())
      .then((data: SettingsData) => {
        setSettings(data);
        setProvider(data.provider);
        setOllamaUrl(data.ollama_url);
        setModelName(data.model_name);
        setKrakenEnabled(data.kraken_enabled);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setTestResult(null);
    const body: Record<string, any> = {
      provider,
      ollama_url: ollamaUrl,
      model_name: modelName,
      kraken_enabled: krakenEnabled,
    };
    // Only send API key if user entered a new one
    if (apiKey) body.api_key = apiKey;

    const res = await fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    setSettings(data);
    setApiKey('');
    setSaving(false);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch('/api/settings/test-connection', { method: 'POST' });
      const data = await res.json();
      setTestResult(data);
    } catch (e: any) {
      setTestResult({ status: 'error', message: e.message });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="font-body text-slate-ink/40 text-sm">Loading settings...</p>
      </div>
    );
  }

  const providerOptions = [
    {
      id: 'claude',
      name: 'Claude API',
      description: 'Anthropic Claude — best accuracy, requires API key (~$0.05-0.15/page)',
      icon: '🧠',
    },
    {
      id: 'ollama',
      name: 'Ollama (Local)',
      description: 'Run vision models locally — free, private, no API key needed',
      icon: '🏠',
    },
    {
      id: 'none',
      name: 'None (Kraken only)',
      description: 'Skip LLM extraction — use Kraken OCR for raw text only',
      icon: '📝',
    },
  ];

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h2 className="font-heading text-3xl font-bold text-slate-ink mb-1">Settings</h2>
        <p className="font-body text-slate-ink/50 text-sm">
          Configure the extraction model and OCR pipeline.
        </p>
      </div>

      {/* Provider selection */}
      <div className="mb-8">
        <h3 className="font-heading text-lg font-semibold text-slate-ink mb-3">
          Extraction Model
        </h3>
        <div className="space-y-2">
          {providerOptions.map((opt) => (
            <button
              key={opt.id}
              onClick={() => setProvider(opt.id)}
              className={`w-full flex items-start gap-3 p-4 rounded-lg border text-left transition-colors ${
                provider === opt.id
                  ? 'border-archive-amber bg-amber-50/50'
                  : 'border-parchment bg-white hover:border-archive-amber/30'
              }`}
            >
              <span className="text-xl mt-0.5">{opt.icon}</span>
              <div>
                <p className={`font-body text-sm font-semibold ${
                  provider === opt.id ? 'text-archive-amber' : 'text-slate-ink'
                }`}>
                  {opt.name}
                </p>
                <p className="font-body text-xs text-slate-ink/50 mt-0.5">{opt.description}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Claude settings */}
      {provider === 'claude' && (
        <div className="mb-8 p-5 bg-white border border-parchment rounded-lg space-y-4">
          <h3 className="font-heading text-base font-semibold text-slate-ink">Claude API Settings</h3>
          <div>
            <label className="block font-body text-xs text-slate-ink/60 mb-1">
              API Key {settings?.api_key_set && <span className="text-trust-verified">(saved)</span>}
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={settings?.api_key_set ? '••••••••••••••••' : 'sk-ant-...'}
              className="w-full h-9 px-3 border border-parchment rounded-lg font-mono text-sm text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
            />
            <p className="font-body text-xs text-slate-ink/40 mt-1">
              Get your key at console.anthropic.com. Stored locally, never sent anywhere except Anthropic.
            </p>
          </div>
          <div>
            <label className="block font-body text-xs text-slate-ink/60 mb-1">Model</label>
            <select
              value={modelName || ''}
              onChange={(e) => setModelName(e.target.value)}
              className="w-full h-9 px-3 border border-parchment rounded-lg font-body text-sm text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
            >
              <option value="">Default (Claude Sonnet 4)</option>
              <option value="claude-sonnet-4-20250514">Claude Sonnet 4</option>
              <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5 (faster, cheaper)</option>
              <option value="claude-opus-4-20250514">Claude Opus 4 (most capable)</option>
            </select>
          </div>
        </div>
      )}

      {/* Ollama settings */}
      {provider === 'ollama' && (
        <div className="mb-8 p-5 bg-white border border-parchment rounded-lg space-y-4">
          <h3 className="font-heading text-base font-semibold text-slate-ink">Ollama Settings</h3>
          <div>
            <label className="block font-body text-xs text-slate-ink/60 mb-1">Ollama URL</label>
            <input
              type="text"
              value={ollamaUrl}
              onChange={(e) => setOllamaUrl(e.target.value)}
              className="w-full h-9 px-3 border border-parchment rounded-lg font-mono text-sm text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
            />
          </div>
          <div>
            <label className="block font-body text-xs text-slate-ink/60 mb-1">Model name</label>
            <input
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="llama3.2-vision (default)"
              className="w-full h-9 px-3 border border-parchment rounded-lg font-mono text-sm text-slate-ink bg-ivory focus:outline-none focus:border-archive-amber transition-colors"
            />
            <p className="font-body text-xs text-slate-ink/40 mt-1">
              Must be a vision-capable model. Install with: <code className="font-mono bg-parchment px-1 rounded">ollama pull llama3.2-vision</code>
            </p>
          </div>
        </div>
      )}

      {/* Kraken OCR */}
      <div className="mb-8 p-5 bg-white border border-parchment rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-heading text-base font-semibold text-slate-ink">Kraken OCR</h3>
            <p className="font-body text-xs text-slate-ink/50 mt-0.5">
              Local text extraction before LLM processing. Free, runs offline.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {settings?.kraken_available ? (
              <span className="text-xs font-body text-trust-verified bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                Installed
              </span>
            ) : (
              <span className="text-xs font-body text-slate-ink/40 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                Not installed
              </span>
            )}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={krakenEnabled}
                onChange={(e) => setKrakenEnabled(e.target.checked)}
                disabled={!settings?.kraken_available}
                className="accent-archive-amber"
              />
              <span className="font-body text-sm text-slate-ink">Enable</span>
            </label>
          </div>
        </div>
        {!settings?.kraken_available && (
          <p className="font-body text-xs text-slate-ink/40 mt-2">
            Install in Docker: Kraken is included in the Docker image automatically.
            <br />
            Install locally: <code className="font-mono bg-parchment px-1 rounded">pip install kraken</code> (requires PyTorch, ~2GB)
          </p>
        )}
      </div>

      {/* Current config summary */}
      <div className="mb-6 p-4 bg-parchment/30 rounded-lg">
        <p className="font-body text-xs text-slate-ink/50">
          Active model: <span className="font-mono text-slate-ink/70">{settings?.effective_model || 'none'}</span>
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-5 h-9 rounded-lg bg-archive-amber text-white font-body text-sm hover:bg-archive-amber-light transition-colors disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
        <button
          onClick={handleTest}
          disabled={testing}
          className="px-4 h-9 rounded-lg border border-parchment font-body text-sm text-slate-ink/60 hover:border-archive-amber hover:text-archive-amber transition-colors disabled:opacity-50"
        >
          {testing ? 'Testing...' : 'Test Connection'}
        </button>
      </div>

      {testResult && (
        <div
          className={`mt-4 p-3 rounded-lg border ${
            testResult.status === 'ok'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
              : 'bg-red-50 border-red-200 text-red-700'
          }`}
        >
          <p className="font-body text-sm">{testResult.message}</p>
          {testResult.models && (
            <p className="font-mono text-xs mt-1 opacity-70">
              Available: {testResult.models.join(', ')}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
