(() => {
  "use strict";

  const REPO_DATA_PATH = "./repo-data.json";

  async function loadRepoData() {
    const response = await fetch(REPO_DATA_PATH, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Failed to load ${REPO_DATA_PATH}: ${response.status}`);
    }
    const data = await response.json();
    if (!Array.isArray(data)) {
      throw new Error("Invalid repo-data.json format: expected an array");
    }
    return data;
  }

  function uniqueValues(rows, key) {
    const values = new Set();
    for (const row of rows) {
      const value = String(row[key] ?? "").trim();
      if (value) values.add(value);
    }
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }

  function applyFilters(rows, filters) {
    return rows.filter((row) => {
      const byTopic = !filters.topic || row.topic === filters.topic;
      const byRelevance = !filters.relevance || row.relevance === filters.relevance;
      const byRisk = !filters.risk || row.risk === filters.risk;
      const byPriority =
        !filters.adoption_priority || row.adoption_priority === filters.adoption_priority;
      return byTopic && byRelevance && byRisk && byPriority;
    });
  }

  window.RepoData = {
    REPO_DATA_PATH,
    loadRepoData,
    uniqueValues,
    applyFilters,
  };
})();

