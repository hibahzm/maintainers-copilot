import React from "react";
import { createRoot } from "react-dom/client";

function App() {
  return (
    <main>
      <h1>Maintainers Copilot Widget</h1>
      <p>Widget shell created. Streaming chat arrives later.</p>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);

export default App;
