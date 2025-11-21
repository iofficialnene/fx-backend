// frontend/src/api.js
const DEFAULT_BACKEND = "https://backend-qxff.onrender.com"; // your backend URL
const BACKEND_URL = process.env.REACT_APP_API_URL || process.env.VITE_API_URL || DEFAULT_BACKEND;

export async function fetchConfluence() {
  const url = `${BACKEND_URL.replace(/\/$/, "")}/confluence`;
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}
