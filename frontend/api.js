// The only boundary between the dashboard and the demo HTTP API.
async function request(path, options) {
  const response = await fetch(path, options);
  let data;
  try { data = await response.json(); } catch { throw new Error(`Unexpected response from ${path}`); }
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
export const api = {
  config: profile => request(`/api/config${profile ? `?profile=${encodeURIComponent(profile)}` : ''}`),
  content: () => request('/api/content'),
  runs: async () => (await request('/api/runs')).runs || [],
  run: id => request(`/api/runs/${encodeURIComponent(id)}`),
  start: body => request('/api/runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
};
export function normalizeReplays(value) {
  if (!value) return null;
  if (!value.traces) return value;
  return Object.fromEntries(Object.entries(value.traces).map(([key, entry]) => [key, {
    ...value.scenario, ...entry.trace, weapons: entry.weapons, config_sha256: entry.config_sha256,
  }]));
}
