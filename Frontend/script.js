let latestData = null; // Store the last response for CSV export

document.getElementById("analyzeForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const url = document.getElementById("urlInput").value;
  const resultDiv = document.getElementById("result");
  const loadingDiv = document.getElementById("loading");
  const submitBtn = document.getElementById("submitBtn");

  resultDiv.classList.add("hidden");
  resultDiv.classList.remove("visible");
  loadingDiv.classList.remove("hidden");
  submitBtn.disabled = true;
  document.getElementById("downloadBtn").classList.add("hidden");

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    const data = await response.json();
    latestData = data;

    document.getElementById("contactsList").innerHTML =
      data.contacts.map(c => `<li>${c}</li>`).join("");

    document.getElementById("leadersList").innerHTML =
      data.leadership.map(l =>
        `<li>${l.profile}${l.linkedin ? ` – <a href="${l.linkedin}" target="_blank">LinkedIn</a>` : ""}</li>`
      ).join("");

    document.getElementById("linksList").innerHTML =
      data.links.map(link => `<li><a href="${link}" target="_blank">${link}</a></li>`).join("");

    document.getElementById("swotStrengths").innerHTML =
      data.swot.Strengths.map(s => `<li>${s}</li>`).join("");
    document.getElementById("swotWeaknesses").innerHTML =
      data.swot.Weaknesses.map(w => `<li>${w}</li>`).join("");
    document.getElementById("swotOpportunities").innerHTML =
      data.swot.Opportunities.map(o => `<li>${o}</li>`).join("");
    document.getElementById("swotThreats").innerHTML =
      data.swot.Threats.map(t => `<li>${t}</li>`).join("");

    loadingDiv.classList.add("hidden");
    resultDiv.classList.remove("hidden");
    requestAnimationFrame(() => resultDiv.classList.add("visible"));
    document.getElementById("downloadBtn").classList.remove("hidden");
  } catch (err) {
    alert("Error analyzing site: " + err.message);
    console.error(err);
    loadingDiv.classList.add("hidden");
  } finally {
    submitBtn.disabled = false;
  }
});

document.getElementById("downloadBtn").addEventListener("click", () => {
  if (!latestData) return alert("No data to download.");

  const { links, contacts, leadership, swot } = latestData;

  let csvContent = "data:text/csv;charset=utf-8,";

  function addSection(title, rows) {
    csvContent += `"${title}"\n`;
    rows.forEach(row => {
      csvContent += `"${row.replace(/"/g, '""')}"\n`;
    });
    csvContent += "\n";
  }

  addSection("Discovered Links", links);
  addSection("Contacts", contacts);
  addSection("Leadership", leadership.map(l =>
    `${l.profile}${l.linkedin ? ` (LinkedIn: ${l.linkedin})` : ""}`
  ));
  addSection("SWOT - Strengths", swot.Strengths);
  addSection("SWOT - Weaknesses", swot.Weaknesses);
  addSection("SWOT - Opportunities", swot.Opportunities);
  addSection("SWOT - Threats", swot.Threats);

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", "company_analysis.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});
