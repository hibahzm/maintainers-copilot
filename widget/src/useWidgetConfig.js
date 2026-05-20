export async function fetchWidgetConfig({ apiBase, widgetId, hostOrigin }) {
  const response = await fetch(`${apiBase}/widget/config/${encodeURIComponent(widgetId)}`, {
    headers: { "X-Widget-Origin": hostOrigin },
  });
  if (!response.ok) {
    throw new Error(`Widget config failed with HTTP ${response.status}`);
  }
  return response.json();
}
