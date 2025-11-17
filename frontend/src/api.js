// Frontend API wrapper
const API = (path) => {
  // For local dev use http://localhost:5000, on Render it will be same origin if backend served there.
  const base = import.meta.env.VITE_API_URL || "";
  return fetch(base + path).then(r => r.json());
};

export const fetchConfluence = () => API("/confluence");
