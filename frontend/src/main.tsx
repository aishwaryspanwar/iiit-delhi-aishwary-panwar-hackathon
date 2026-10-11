import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/google-sans-flex/400.css";
import "@fontsource/google-sans-flex/600.css";
import "./index.css";
import App from "./App";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
