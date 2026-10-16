import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

// Vite injects BASE_URL from `base`; strip the trailing slash for the router
// ("" at the root, "/haze-watch" under the subpath).
const basename = import.meta.env.BASE_URL.replace(/\/+$/, "");

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename={basename}>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
