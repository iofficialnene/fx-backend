// frontend/src/api.js
const DEFAULT_BACKEND = "https://backend-qxff.onrender.com";
const BACKEND_URL =
  import.meta.env.VITE_API_URL ||
  process.env.REACT_APP_API_URL ||
  DEFAULT_BACKEND;

export async function fetchConfluence() {
  const base = BACKEND_URL ? BACKEND_URL.replace(/\/?$/, "") : DEFAULT_BACKEND;
  const url = `${base}/confluence`;

  try {
    const res = await fetch(url, {
      method: "GET",
      headers: {
        "Cache-Control": "no-cache",
        Pragma: "no-cache",
      },
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`API error ${res.status}: ${body}`);
    }

    return await res.json();
  } catch (err) {
    console.error("FetchConfluence error:", err);
    throw new Error("Failed to connect to backend. Check if server is running.");
  }
}
