export const fetchConfluence = async () => {
  try {
    const res = await fetch("https://backend-qxff.onrender.com/confluence");
    const data = await res.json();

    // Convert LIST → DICTIONARY keyed by Pair
    const mapped = {};
    data.forEach(item => {
      mapped[item.Pair] = {
        Confluence: item.Confluence,
        ConfluencePercent: item.ConfluencePercent,
        Summary: item.Summary
      };
    });

    return mapped;

  } catch (err) {
    console.error("fetch error:", err);
    return {};
  }
};