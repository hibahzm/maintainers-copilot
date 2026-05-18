export function notifyParentOfHeight(height) {
  window.parent.postMessage({ type: "widget:resize", height }, "*");
}
