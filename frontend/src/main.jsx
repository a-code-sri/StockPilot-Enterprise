import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
localStorage.removeItem("token");
localStorage.removeItem("user");
createRoot(document.getElementById('root')).render(
  <App />
)
