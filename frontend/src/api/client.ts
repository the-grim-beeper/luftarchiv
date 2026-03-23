const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  listCollections: () => request<any>('/collections'),
  getCollection: (id: string) => request<any>(`/collections/${id}`),
  importFolder: (data: any) => request<any>('/import', { method: 'POST', body: JSON.stringify(data) }),
  startExtraction: (id: string, stage: string, maxPages?: number) => {
    const params = new URLSearchParams({ stage });
    if (maxPages) params.set('max_pages', String(maxPages));
    return request<any>(`/collections/${id}/extract?${params}`, { method: 'POST' });
  },
  deleteCollection: (id: string) =>
    request<any>(`/collections/${id}`, { method: 'DELETE' }),
  search: (filters: any) => request<any>('/search', { method: 'POST', body: JSON.stringify(filters) }),
  listGlossary: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<any>(`/knowledge/glossary${qs}`);
  },
  reviewGlossary: (id: string, action: any) =>
    request<any>(`/knowledge/glossary/${id}/review`, { method: 'POST', body: JSON.stringify(action) }),
  exportCsv: (collectionId: string) => `${BASE_URL}/export/${collectionId}/csv`,
};
