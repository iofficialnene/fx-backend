// src/api.js

const API_BASE = "https://backend-qxff.onrender.com";

export async function fetchConfluence() {
  try {
    const res = await fetch(`${API_BASE}/confluence`, {
      method: "GET",
      headers: { "Content-Type": "application/json" }
    });

    if (!res.ok) {
      throw new Error(`Backend error: ${res.status}`);
    }

    return await res.json();
  } catch (err) {
    console.error("fetchConfluence ERROR:", err);
    return null;
  }
}