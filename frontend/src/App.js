import React, { useEffect, useState } from "react";

function App() {
  const backendURL = "http://192.168.40.146:5000/data";

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [intervalSec, setIntervalSec] = useState(5);

  // Fetch function
  const fetchData = async () => {
    try {
      setLoading(true);

      const res = await fetch(backendURL);
      const json = await res.json();

      setData(json);
      setError(null);
    } catch (err) {
      setError("Failed to connect to backend");
    } finally {
      setLoading(false);
    }
  };

  // Run on first load
  useEffect(() => {
    fetchData();
  }, []);

  // Auto refresh effect
  useEffect(() => {
    if (!autoRefresh) return;

    const t = setInterval(fetchData, intervalSec * 1000);
    return () => clearInterval(t);
  }, [autoRefresh, intervalSec]);

  return (
    <div style={{ padding: "20px", fontFamily: "Arial", color: "#333" }}>
      <h1>FX Confluence Dashboard</h1>

      {/* Status UI */}
      <div style={{ marginTop: "20px" }}>
        {loading && <p>Loading...</p>}
        {error && <p style={{ color: "red" }}>{error}</p>}

        {data && (
          <div style={{ marginTop: "10px" }}>
            <p><strong>Status:</strong> {data.status}</p>
            <p><strong>Message:</strong> {data.message}</p>

            {/* Example if you return extra values */}
            {data.values && Array.isArray(data.values) && (
              <div>
                <strong>Values:</strong>
                <ul>
                  {data.values.map((v, index) => (
                    <li key={index}>{v}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Controls */}
      <div style={{ marginTop: "30px" }}>
        <button onClick={fetchData} style={btnStyle}>
          Refresh
        </button>

        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          style={{ ...btnStyle, marginLeft: "10px" }}
        >
          Auto Refresh: {autoRefresh ? `${intervalSec}s` : "OFF"}
        </button>

        <button
          onClick={() => setIntervalSec(intervalSec + 5)}
          style={{ ...btnStyle, marginLeft: "10px" }}
        >
          +5s
        </button>
      </div>
    </div>
  );
}

const btnStyle = {
  padding: "10px 15px",
  backgroundColor: "#007bff",
  border: "none",
  borderRadius: "5px",
  color: "white",
  cursor: "pointer",
};

export default App;
