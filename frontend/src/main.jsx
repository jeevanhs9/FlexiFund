import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";
import "./ui-system.css";
import "./glassmorphism-premium.css";
import { initScrollAnimations } from "./scroll-animations.js";

// Initialize scroll animations after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initScrollAnimations();
});

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
