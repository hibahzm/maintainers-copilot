export async function useWidgetConfig(widgetId) {
  const response = await fetch(`/widget/config/${widgetId}`);
  return response.json();
}
