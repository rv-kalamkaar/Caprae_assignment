// frontend/script.js
document.getElementById('analyze-form').addEventListener('submit', async function (e) {
  e.preventDefault();

  const url = document.getElementById('url').value.trim();
  if (!url) return;

  const resultsDiv = document.getElementById('results');
  resultsDiv.classList.remove('hidden');
  resultsDiv.innerHTML = '<p>Loading...</p>';

  try {
    const res = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    const data = await res.json();
    if (data.error) throw new Error(data.error);

    resultsDiv.innerHTML = `
      <h2>Analysis Results</h2>
      <div><strong>Discovered Links:</strong><ul id="links">${data.discovered_links.map(link => `<li><a href="${link}" target="_blank">${link}</a></li>`).join('')}</ul></div>
      <div><strong>Leadership:</strong><ul id="leaders">${data.leaders.map(l => `<li>${l}</li>`).join('')}</ul></div>
      <div><strong>Technology Stack:</strong><ul id="tech">${data.tech_stack.map(t => `<li>${t}</li>`).join('')}</ul></div>
      <div><strong>SWOT Analysis:</strong>
        <div class="swot">
          <div><h3>Strengths</h3><ul id="swot-strengths">${data.swot.Strengths.map(i => `<li>${i}</li>`).join('')}</ul></div>
          <div><h3>Weaknesses</h3><ul id="swot-weaknesses">${data.swot.Weaknesses.map(i => `<li>${i}</li>`).join('')}</ul></div>
          <div><h3>Opportunities</h3><ul id="swot-opportunities">${data.swot.Opportunities.map(i => `<li>${i}</li>`).join('')}</ul></div>
          <div><h3>Threats</h3><ul id="swot-threats">${data.swot.Threats.map(i => `<li>${i}</li>`).join('')}</ul></div>
        </div>
      </div>
    `;
  } catch (err) {
    resultsDiv.innerHTML = `<p class="error">Error: ${err.message}</p>`;
  }
});
