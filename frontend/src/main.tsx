import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App.tsx"
import { initDemoMode } from "./lib/api"

// Check for demo mode before rendering — auto-injects the admin key
// so visitors skip the login page on the public demo instance.
initDemoMode().finally(() => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
