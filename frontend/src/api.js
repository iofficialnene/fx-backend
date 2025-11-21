// src/api.js

const BASE_URL = "https://backend-qxff.onrender.com";

export async function fetchConfluence() {
  try {
    const response = await fetch(`${BASE_URL}/confluence`);
    if (!response.ok) {
      throw new Error("Failed to fetch confluence data");
    }
    return await response.json();
  } catch (error) {
    console.error("fetchConfluence error:", error);
    return [];
  }
}
