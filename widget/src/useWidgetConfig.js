export async function fetchWidgetConfig({ apiBase, widgetId }) {
  const response = await fetch(`${apiBase}/widget/config/${encodeURIComponent(widgetId)}`);
  if (!response.ok) {
    throw new Error(`Widget config failed with HTTP ${response.status}`);
  }
  return response.json();
}
