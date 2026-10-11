/**
 * FRONTEND LAYER: script.js
 * File: frontend/script.js
 * Project: TransitMatch (Team BYTEFORCE - CBC006)
 * College: Ballari Institute of Technology and Management
 * Domain: Software & Web Development
 * Problem Statement: PS-3 Public Transport Lost-and-Found Matching
 */

// Global Application State
let currentRole = 'passenger';
let allItemsCache = [];
let activeChatLang = 'en';

// DOM Initialization
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  await loadDashboardData();
  await loadItems();
  await loadIncidentPatterns();
  refreshAllDropdowns();
}

// -------------------------------------------------------------
// 1. Role & Tab Controllers
// -------------------------------------------------------------
function handleRoleChange(role) {
  currentRole = role;
  document.body.setAttribute('data-role', role);
  showToast(`Switched active role to: ${role.toUpperCase()}`, 'info');

  // If switched to passenger and currently viewing a staff-only tab, switch back to browse
  if (role === 'passenger') {
    const activePanel = document.querySelector('.tab-panel.active')?.id;
    if (activePanel === 'tab-dashboard' || activePanel === 'tab-handover' || activePanel === 'tab-patterns') {
      switchTab('tab-browse');
    }
  }

  loadItems();
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  
  const targetPanel = document.getElementById(tabId);
  if (targetPanel) targetPanel.classList.add('active');
  
  const matchingBtn = document.querySelector(`button[onclick="switchTab('${tabId}')"]`);
  if (matchingBtn) matchingBtn.classList.add('active');

  if (tabId === 'tab-dashboard') loadDashboardData();
  else if (tabId === 'tab-matching') populateMatchTargetSelector();
  else if (tabId === 'tab-verify') loadFoundItemsForClaim();
  else if (tabId === 'tab-handover') loadHandoverEligibleItems();
  else if (tabId === 'tab-patterns') loadIncidentPatterns();
}

async function loadDashboardData() {
  try {
    const res = await fetch('/api/dashboard/stats');
    const data = await res.json();
    if (!data.success) return;

    const s = data.stats;
    document.getElementById('dashRecoveryRate').textContent = `${s.recovery_rate}%`;
    document.getElementById('dashLostCount').textContent = s.lost_count;
    document.getElementById('dashFoundCount').textContent = s.found_count;
    document.getElementById('dashMatchesCount').textContent = s.matches_evaluated;

    const sm = s.status_map || {};
    document.getElementById('pipeReported').textContent = sm['REPORTED'] || 0;
    document.getElementById('pipePotential').textContent = sm['POTENTIAL_MATCH'] || 0;
    document.getElementById('pipeUnderReview').textContent = sm['CLAIM_UNDER_VERIFICATION'] || 0;
    document.getElementById('pipeVerified').textContent = sm['VERIFIED'] || 0;
    document.getElementById('pipeHandedOver').textContent = sm['HANDED_OVER'] || 0;

    const routeContainer = document.getElementById('routeHotspotsList');
    if (routeContainer && s.routes) {
      const maxCount = Math.max(...s.routes.map(r => r.count), 1);
      routeContainer.innerHTML = s.routes.map(r => `
        <div class="dist-item-row">
          <div class="dist-labels">
            <span><i class="fa-solid fa-bus text-cyan"></i> ${escapeHtml(r.route)}</span>
            <strong>${r.count} incidents</strong>
          </div>
          <div class="dist-bar-track">
            <div class="dist-bar-fill" style="width: ${(r.count / maxCount) * 100}%;"></div>
          </div>
        </div>
      `).join('');
    }

    const catContainer = document.getElementById('categoryDistList');
    if (catContainer && s.categories) {
      const maxCat = Math.max(...s.categories.map(c => c.count), 1);
      catContainer.innerHTML = s.categories.map(c => `
        <div class="dist-item-row">
          <div class="dist-labels">
            <span><i class="fa-solid fa-tag text-cyan"></i> ${escapeHtml(c.category)}</span>
            <strong>${c.count} items</strong>
          </div>
          <div class="dist-bar-track">
            <div class="dist-bar-fill" style="width: ${(c.count / maxCat) * 100}%;"></div>
          </div>
        </div>
      `).join('');
    }

    const feedContainer = document.getElementById('dashboardActivityFeed');
    if (feedContainer && s.recent_activities) {
      feedContainer.innerHTML = s.recent_activities.map(a => `
        <div class="activity-feed-item">
          <i class="fa-solid fa-circle-dot"></i>
          <div style="flex: 1;">
            <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--text-muted); font-family: var(--font-mono);">
              <span>${escapeHtml(a.timestamp)}</span>
              <span class="badge-tag">${escapeHtml(a.actor_role)}</span>
            </div>
            <div style="font-weight: 600; color: #fff; margin-top: 2px;">
              ${escapeHtml(a.title)}: <span class="text-cyan">${escapeHtml(a.new_status)}</span>
            </div>
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px;">
              ${escapeHtml(a.remarks || 'Status logged in immutable trail.')}
            </div>
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Error loading dashboard stats:', err);
  }
}


// -------------------------------------------------------------
// 2. Registry & Privacy-Preserving Item Search
// -------------------------------------------------------------
async function loadItems() {
  const grid = document.getElementById('itemsGrid');
  grid.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Fetching records...</div>';

  const type = document.getElementById('typeFilter')?.value || '';
  const cat = document.getElementById('categoryFilter')?.value || '';
  const q = document.getElementById('searchInput')?.value || '';

  try {
    const url = `/api/items?type=${encodeURIComponent(type)}&category=${encodeURIComponent(cat)}&q=${encodeURIComponent(q)}&role=${currentRole}`;
    const res = await fetch(url);
    const data = await res.json();

    if (data.success) {
      allItemsCache = data.items;
      updateStats(data.items);
      renderItemsList(data.items);
      refreshAllDropdowns();
    } else {
      grid.innerHTML = `<div class="empty-state">Failed to load items: ${data.error}</div>`;
    }
  } catch (err) {
    grid.innerHTML = `<div class="empty-state">Could not connect to backend server.</div>`;
  }
}

function filterItems() {
  const query = (document.getElementById('searchInput')?.value || '').toLowerCase();
  const typeFilter = document.getElementById('typeFilter')?.value || '';
  const catFilter = document.getElementById('categoryFilter')?.value || '';

  const filtered = allItemsCache.filter(item => {
    const matchesQuery = !query || 
      item.title.toLowerCase().includes(query) ||
      item.description.toLowerCase().includes(query) ||
      item.route_vehicle.toLowerCase().includes(query) ||
      item.color.toLowerCase().includes(query);

    const matchesType = !typeFilter || item.report_type === typeFilter;
    const matchesCat = !catFilter || item.category === catFilter;

    return matchesQuery && matchesType && matchesCat;
  });

  renderItemsList(filtered);
}

function renderItemsList(items) {
  const grid = document.getElementById('itemsGrid');
  if (!items || items.length === 0) {
    grid.innerHTML = `
      <div class="empty-state full-width">
        <i class="fa-solid fa-folder-open fa-3x"></i>
        <h3>No matching transit items found</h3>
      </div>`;
    return;
  }

  grid.innerHTML = items.map(item => `
    <div class="item-card">
      <div>
        <div class="item-card-top">
          <span class="type-pill type-${item.report_type}">
            ${item.report_type === 'lost' ? '<i class="fa-solid fa-triangle-exclamation"></i> Lost Report' : '<i class="fa-solid fa-box"></i> Found in Custody'}
          </span>
          <span class="status-badge ${item.status}">${item.status.replace(/_/g, ' ')}</span>
        </div>

        <h3 class="item-title">${escapeHtml(item.title)}</h3>
        <p class="item-desc">${escapeHtml(item.description)}</p>

        <div class="item-meta-list">
          <div class="item-meta-row">
            <i class="fa-solid fa-bus"></i>
            <span><strong>Route:</strong> ${escapeHtml(item.route_vehicle)}</span>
          </div>
          <div class="item-meta-row">
            <i class="fa-solid fa-palette"></i>
            <span><strong>Color & Brand:</strong> ${escapeHtml(item.color)} • ${escapeHtml(item.brand || 'Unbranded')}</span>
          </div>
          <div class="item-meta-row">
            <i class="fa-solid fa-location-dot"></i>
            <span><strong>Location:</strong> ${escapeHtml(item.incident_location || item.current_depot || 'In Transit')}</span>
          </div>
          <div class="item-meta-row">
            <i class="fa-solid fa-clock"></i>
            <span><strong>Time:</strong> ${escapeHtml(item.incident_time)}</span>
          </div>
        </div>

        <div class="privacy-badge">
          <i class="fa-solid fa-shield-halved"></i>
          <span>${escapeHtml(item.secret_clue || 'Private detail protected')}</span>
        </div>
      </div>

      <div class="item-actions">
        <button class="btn btn-outline" style="flex:1" onclick="openMatchTabForItem(${item.id})">
          <i class="fa-solid fa-brain"></i> AI Matches
        </button>
        ${item.report_type === 'found' ? `
        <button class="btn btn-primary" style="flex:1" onclick="openClaimForItem(${item.id})">
          <i class="fa-solid fa-shield-cat"></i> Claim Item
        </button>` : `
        <button class="btn btn-secondary" style="flex:1" onclick="openAuditForItem(${item.id})">
          <i class="fa-solid fa-timeline"></i> Lifecycle
        </button>`}
        <button class="btn btn-delete" onclick="handleDeleteItem(${item.id})" title="Delete report if item was found or resolved">
          <i class="fa-solid fa-trash-can"></i> Delete
        </button>
      </div>
    </div>
  `).join('');
}

async function handleDeleteItem(itemId) {
  const confirmed = confirm(`Are you sure you want to delete Report #${itemId}?\n\nIf the item has been found, restored to owner, or the report was made by mistake, this will permanently remove it from the active registry.`);
  if (!confirmed) return;

  try {
    const res = await fetch(`/api/items/${itemId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      await loadItems();
      await loadDashboardData();
    } else {
      showToast(data.error || 'Failed to delete report', 'error');
    }
  } catch (err) {
    showToast('Error deleting item report', 'error');
  }
}

function updateStats(items) {
  document.getElementById('statTotalItems').textContent = items.length;
  const verified = items.filter(i => i.status === 'VERIFIED' || i.status === 'HANDED_OVER').length;
  document.getElementById('statVerifiedCount').textContent = verified;
}

// -------------------------------------------------------------
// 3. Reporting Actions
// -------------------------------------------------------------
async function handleReportLost(e) {
  e.preventDefault();
  const payload = {
    reporter_name: document.getElementById('lostReporterName').value.trim(),
    reporter_contact: document.getElementById('lostReporterContact').value.trim(),
    title: document.getElementById('lostTitle').value.trim(),
    category: document.getElementById('lostCategory').value,
    color: document.getElementById('lostColor').value.trim(),
    brand: document.getElementById('lostBrand').value.trim(),
    route_vehicle: document.getElementById('lostRoute').value.trim(),
    start_location: document.getElementById('lostStart').value.trim(),
    destination_location: document.getElementById('lostDest').value.trim(),
    incident_location: document.getElementById('lostLoc').value.trim(),
    description: document.getElementById('lostDesc').value.trim(),
    secret_clue: document.getElementById('lostSecretClue').value.trim()
  };

  const res = await fetch('/api/items/lost', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (data.success) {
    showToast(`Report #${data.item_id} registered!`, 'success');
    document.getElementById('lostItemForm').reset();
    await loadItems();
    openMatchTabForItem(data.item_id);
  }
}

async function handleReportFound(e) {
  e.preventDefault();
  const payload = {
    reporter_name: document.getElementById('foundReporterName').value.trim(),
    reporter_contact: document.getElementById('foundReporterContact').value.trim(),
    title: document.getElementById('foundTitle').value.trim(),
    category: document.getElementById('foundCategory').value,
    color: document.getElementById('foundColor').value.trim(),
    brand: document.getElementById('foundBrand').value.trim(),
    route_vehicle: document.getElementById('foundRoute').value.trim(),
    current_depot: document.getElementById('foundDepot').value.trim(),
    description: document.getElementById('foundDesc').value.trim(),
    secret_clue: document.getElementById('foundSecretClue').value.trim()
  };

  const res = await fetch('/api/items/found', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (data.success) {
    showToast(`Found item #${data.item_id} added!`, 'success');
    document.getElementById('foundItemForm').reset();
    await loadItems();
    switchTab('tab-browse');
  }
}

// -------------------------------------------------------------
// 4. AI Multi-Attribute Match Ranking
// -------------------------------------------------------------
function populateMatchTargetSelector() {
  const sel = document.getElementById('matchTargetSelector');
  if (!sel) return;
  sel.innerHTML = '<option value="">-- Choose an item --</option>' + 
    allItemsCache.map(i => `
      <option value="${i.id}">#${i.id} [${i.report_type.toUpperCase()}] ${escapeHtml(i.title)} (${escapeHtml(i.route_vehicle)})</option>
    `).join('');
}

function openMatchTabForItem(itemId) {
  switchTab('tab-matching');
  const sel = document.getElementById('matchTargetSelector');
  if (sel) {
    sel.value = itemId;
    runMatchEvaluation(itemId);
  }
}

async function runMatchEvaluation(itemId) {
  if (!itemId) return;
  const container = document.getElementById('matchEvaluationContainer');
  container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Calculating AI match ranking...</div>';

  const res = await fetch(`/api/matches/${itemId}`);
  const data = await res.json();
  if (!data.success) {
    container.innerHTML = `<div class="empty-state">${data.error}</div>`;
    return;
  }

  const target = data.target;
  const matches = data.matches;
  document.getElementById('statMatchesFound').textContent = matches.length;

  let html = `
    <div class="match-comparison-hero">
      <div>
        <span class="type-pill type-${target.report_type}">Target #${target.id} (${target.report_type.toUpperCase()})</span>
        <h2 style="margin-top:6px;">${escapeHtml(target.title)}</h2>
        <p>${escapeHtml(target.description)}</p>
      </div>
    </div>
  `;

  if (!matches || matches.length === 0) {
    html += `<div class="empty-state"><h3>No opposite candidate items found.</h3></div>`;
  } else {
    html += `<div class="match-candidates-grid">`;
    matches.forEach(m => {
      const cand = m.candidate;
      const evalRes = m.match_evaluation;
      const score = evalRes.confidence_score;
      const tierClass = score >= 75 ? 'high-confidence' : (score >= 50 ? 'probable-match' : 'weak-match');

      html += `
        <div class="candidate-match-card ${tierClass}">
          <div class="candidate-header-row">
            <div>
              <span class="type-pill type-${cand.report_type}">Candidate #${cand.id}</span>
              <h3 style="margin-top:6px;">${escapeHtml(cand.title)}</h3>
              <p class="text-muted">${escapeHtml(cand.description)}</p>
            </div>
            <div style="text-align:right;">
              <div class="score-radial">${score}%</div>
              <div class="badge-tag">${evalRes.badge}</div>
            </div>
          </div>

          <div class="confidence-progress-bar">
            <div class="confidence-progress-fill" style="width: ${score}%;"></div>
          </div>

          <table class="scoring-breakdown-table">
            <thead>
              <tr><th>Factor</th><th>Max</th><th>Earned</th><th>Audit Note</th></tr>
            </thead>
            <tbody>
              ${evalRes.breakdown.map(b => `
                <tr>
                  <td><strong>${escapeHtml(b.factor)}</strong></td>
                  <td>${b.weight}%</td>
                  <td class="earned-cell">+${b.earned}%</td>
                  <td>${escapeHtml(b.note)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>

          <div style="margin-top:16px; text-align:right;">
            <button class="btn btn-primary" onclick="openClaimForItem(${cand.report_type === 'found' ? cand.id : target.id})">
              <i class="fa-solid fa-shield-halved"></i> Verify Secret Clue
            </button>
          </div>
        </div>
      `;
    });
    html += `</div>`;
  }

  container.innerHTML = html;
}

// -------------------------------------------------------------
// 5. Secret-Clue Verification
// -------------------------------------------------------------
function loadFoundItemsForClaim() {
  const sel = document.getElementById('claimFoundItemSelect');
  if (!sel) return;
  const foundItems = allItemsCache.filter(i => i.report_type === 'found');
  sel.innerHTML = '<option value="">-- Select found item in custody --</option>' + 
    foundItems.map(i => `<option value="${i.id}">#${i.id} - ${escapeHtml(i.title)} (${escapeHtml(i.route_vehicle)})</option>`).join('');
}

function openClaimForItem(foundItemId) {
  switchTab('tab-verify');
  const sel = document.getElementById('claimFoundItemSelect');
  if (sel) {
    sel.value = foundItemId;
    loadCompetingClaims(foundItemId);
  }
}

async function loadCompetingClaims(foundItemId) {
  const list = document.getElementById('competingClaimsList');
  if (!foundItemId) return;

  const res = await fetch(`/api/claims/${foundItemId}`);
  const data = await res.json();
  if (data.claims && data.claims.length > 0) {
    list.innerHTML = data.claims.map(c => `
      <div class="claim-entry-card">
        <div style="display:flex; justify-content:space-between;">
          <strong>Claimant: ${escapeHtml(c.claimant_name)}</strong>
          <span class="claim-score-pill">${c.clue_similarity_score}% Match</span>
        </div>
        <div style="font-size:0.8rem; color:var(--text-muted); margin-top:4px;">
          Submitted: "${escapeHtml(c.submitted_secret_clue)}"
        </div>
      </div>
    `).join('');
  } else {
    list.innerHTML = '<div class="empty-state-sm">No competing claims registered yet.</div>';
  }
}

async function handleClaimVerification(e) {
  e.preventDefault();
  const foundId = document.getElementById('claimFoundItemSelect').value;
  const payload = {
    found_item_id: parseInt(foundId),
    claimant_name: document.getElementById('claimantName').value.trim(),
    claimant_contact: document.getElementById('claimantContact').value.trim(),
    secret_clue: document.getElementById('claimantClue').value.trim(),
    supporting_proof_notes: document.getElementById('claimProofNotes').value.trim()
  };

  const resultBox = document.getElementById('verificationResultBox');
  resultBox.style.display = 'block';
  resultBox.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying secret clue...';

  const res = await fetch('/api/claims/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();

  if (data.success) {
    const v = data.verification;
    resultBox.className = `verification-result-box ${v.status}`;
    resultBox.innerHTML = `
      <div style="font-weight:700; font-size:1.05rem; margin-bottom:6px;">
        ${v.status === 'MATCHED' ? '<i class="fa-solid fa-circle-check"></i> Ownership Verified!' : '<i class="fa-solid fa-circle-exclamation"></i> ' + v.status}
      </div>
      <p>${v.message}</p>
      <div style="margin-top:8px; font-size:0.85rem;"><strong>AI Clue Similarity:</strong> ${v.score}%</div>
    `;
    loadCompetingClaims(foundId);
    loadItems();
  }
}

// -------------------------------------------------------------
// 6. Staff Handover & Lifecycle Audit History
// -------------------------------------------------------------
function loadHandoverEligibleItems() {
  const sel = document.getElementById('handoverItemSelect');
  if (!sel) return;
  sel.innerHTML = '<option value="">-- Select item to handover --</option>' + 
    allItemsCache.map(i => `<option value="${i.id}">#${i.id} - ${escapeHtml(i.title)} [${i.status}]</option>`).join('');
}

function openAuditForItem(itemId) {
  switchTab('tab-handover');
  const sel = document.getElementById('handoverItemSelect');
  if (sel) {
    sel.value = itemId;
    loadAuditHistory(itemId);
  }
}

async function loadAuditHistory(itemId) {
  const container = document.getElementById('auditTimelineContainer');
  if (!itemId) return;

  const res = await fetch(`/api/history/${itemId}`);
  const data = await res.json();

  if (data.history && data.history.length > 0) {
    container.innerHTML = data.history.map(h => `
      <div class="timeline-entry">
        <div class="timeline-time">${escapeHtml(h.timestamp)}</div>
        <div class="timeline-title">${escapeHtml(h.new_status)} (${escapeHtml(h.changed_by)})</div>
        <div class="timeline-remarks">${escapeHtml(h.remarks || '')}</div>
      </div>
    `).join('');
  } else {
    container.innerHTML = '<div class="empty-state-sm">No lifecycle history logged yet.</div>';
  }
}

async function handleHandoverSubmit(e) {
  e.preventDefault();
  const itemId = document.getElementById('handoverItemSelect').value;
  const payload = {
    staff_name: document.getElementById('handoverStaffName').value.trim(),
    recipient_name: document.getElementById('handoverRecipientName').value.trim(),
    id_proof_type: document.getElementById('handoverIdProof').value,
    remarks: document.getElementById('handoverRemarks').value.trim()
  };

  const res = await fetch(`/api/items/${itemId}/handover`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (data.success) {
    showToast('Handover logged in audit trail!', 'success');
    await loadItems();
    loadAuditHistory(itemId);
  }
}

// -------------------------------------------------------------
// 7. Incident Patterns & Duplicates
// -------------------------------------------------------------
async function loadIncidentPatterns() {
  const container = document.getElementById('patternsContainer');
  if (!container) return;

  const res = await fetch('/api/patterns');
  const data = await res.json();
  const all = [...(data.live_detected_patterns || []), ...(data.stored_history || [])];
  document.getElementById('statPatternsAlert').textContent = all.length;

  if (all.length === 0) {
    container.innerHTML = `<div class="empty-state">No pattern flags detected.</div>`;
    return;
  }

  container.innerHTML = all.map(p => `
    <div class="pattern-card ${p.type}">
      <div class="pattern-type">${p.type} (${p.confidence}% confidence)</div>
      <h4>${escapeHtml(p.route ? 'Route: ' + p.route : 'Cross-Report')}</h4>
      <p style="font-size:0.88rem;">${escapeHtml(p.description)}</p>
    </div>
  `).join('');
}

// -------------------------------------------------------------
// 8. Multilingual AI Assistant Chatbot
// -------------------------------------------------------------
function toggleChatbot() {
  const win = document.getElementById('chatbotWindow');
  win.style.display = (win.style.display === 'flex') ? 'none' : 'flex';
}

function handleChatLangChange(lang) {
  activeChatLang = lang;
  const greeting = lang === 'hi' ? "नमस्ते! मैं ट्रांजिटमैच एआई सहायक हूँ।" : (lang === 'kn' ? "ನಮಸ್ಕಾರ! ನಾನು ಟ್ರಾನ್ಸಿಟ್‌ಮ್ಯಾಚ್ ಎಐ ಸಹಾಯಕ." : "Language switched to English.");
  appendChatBubble(greeting, 'bot');
}

function sendQuickPrompt(text) {
  document.getElementById('chatInput').value = text;
  sendChatMessage();
}

async function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg) return;

  appendChatBubble(msg, 'user');
  input.value = '';

  const res = await fetch('/api/chatbot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg, lang: activeChatLang })
  });
  const data = await res.json();
  if (data.success) appendChatBubble(data.response, 'bot');
}

function appendChatBubble(text, sender) {
  const msgs = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = `chat-bubble ${sender}-bubble`;
  div.textContent = text;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

// -------------------------------------------------------------
// 9. Demo Scenario Seeder
// -------------------------------------------------------------
async function loadDemoScenario() {
  showToast('Seeding presentation demonstration scenarios...', 'info');
  const res = await fetch('/api/demo/seed', { method: 'POST' });
  const data = await res.json();
  if (data.success) {
    showToast('Demo data seeded successfully!', 'success');
    await loadItems();
    await loadIncidentPatterns();
    switchTab('tab-browse');
  }
}

function refreshAllDropdowns() {
  populateMatchTargetSelector();
  loadFoundItemsForClaim();
  loadHandoverEligibleItems();
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}
