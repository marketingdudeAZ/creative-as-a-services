/**
 * RPM Living — Video Creative Review Portal
 * Client-side JS for feedback submission, approvals, and budget simulator.
 */

(function () {
  "use strict";

  // Extract URL parameters
  const pathParts = window.location.pathname.split("/");
  const UUID = pathParts[pathParts.indexOf("creative-review") + 1] || "";
  const MONTH = pathParts[pathParts.indexOf("creative-review") + 2] || "";
  const TOKEN = new URLSearchParams(window.location.search).get("token") || "";
  const API_BASE = window.PORTAL_API_BASE || "";

  let portalData = null;

  // --- API helpers ---

  async function apiPost(endpoint, body) {
    const resp = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, uuid: UUID, month: MONTH, token: TOKEN }),
    });
    return resp.json();
  }

  async function apiGet(endpoint) {
    const resp = await fetch(
      `${API_BASE}${endpoint}?token=${encodeURIComponent(TOKEN)}`
    );
    return resp.json();
  }

  // --- Initialize ---

  async function loadPortalData() {
    try {
      portalData = await apiGet(`/api/status/${UUID}/${MONTH}`);
      renderPortal();
    } catch (err) {
      document.getElementById("portal-root").innerHTML =
        '<div class="portal-section"><p>Unable to load creative data. Please check your link.</p></div>';
    }
  }

  // --- Render ---

  function renderPortal() {
    if (!portalData) return;

    // Header
    const statusClass = {
      Pending: "status-pending",
      Approved: "status-approved",
      "Partial Approval": "status-partial",
      "Revision Requested": "status-revision",
    }[portalData.approval_status] || "status-pending";

    document.getElementById("property-name").textContent = portalData.property_name;
    document.getElementById("package-tier").textContent = portalData.package_tier;
    const badge = document.getElementById("status-badge");
    badge.textContent = portalData.approval_status;
    badge.className = `status-badge ${statusClass}`;

    // Rationale
    document.getElementById("rationale-text").textContent = portalData.rationale;

    // Video gallery
    renderVideoGallery();

    // Budget simulator
    if (portalData.package_tier !== "Premium" && portalData.performance_snapshot) {
      renderBudgetSimulator();
      document.getElementById("simulator-section").style.display = "block";
    }

    // Revision counter
    document.querySelectorAll(".revision-counter").forEach((el) => {
      el.textContent = `Revision ${portalData.revision_count} of ${portalData.max_revisions} used this month`;
    });
  }

  function renderVideoGallery() {
    const container = document.getElementById("video-gallery");
    container.innerHTML = "";

    const scripts = portalData.scripts || [];
    const urls = portalData.video_urls || [];

    scripts.forEach((script, idx) => {
      const videoData = urls.find((v) => v.script_id === script.script_id) || {};
      const card = createVideoCard(script, videoData, idx);
      container.appendChild(card);
    });

    // Approve All button
    if (scripts.length > 0 && portalData.approval_status !== "Approved") {
      const approveAllDiv = document.createElement("div");
      approveAllDiv.style.marginTop = "16px";
      approveAllDiv.innerHTML =
        '<button class="btn btn-approve-all" onclick="approveAll()">Approve All Variants</button>';
      container.appendChild(approveAllDiv);
    }
  }

  function createVideoCard(script, videoData, idx) {
    const card = document.createElement("div");
    card.className = "video-card";
    card.id = `card-${script.script_id}`;

    card.innerHTML = `
      <div class="video-meta-badge">
        <span>${script.video_length}s</span>
        <span>${script.aspect_ratio}</span>
        <span>${script.target_platform}</span>
      </div>
      <div class="video-card-content">
        <div class="video-player">
          ${videoData.url
            ? `<video controls preload="metadata"><source src="${videoData.url}" type="video/mp4"></video>`
            : '<p style="color:#666">Video processing...</p>'}
        </div>
        <div class="script-panel">
          <div class="script-section"><label>Hook</label><p>${script.hook}</p></div>
          <div class="script-section"><label>Body</label><p>${script.body}</p></div>
          <div class="script-section"><label>Call to Action</label><p>${script.cta}</p></div>
        </div>
      </div>
      <div class="video-actions">
        <button class="btn btn-approve" onclick="approveVariant('${script.script_id}')">Approve</button>
        <button class="btn btn-edit" onclick="toggleFeedback('${script.script_id}')">Request Edits</button>
      </div>
      <div class="feedback-panel" id="feedback-${script.script_id}">
        <div class="feedback-grid">
          <div class="feedback-field">
            <label>Tone Shift</label>
            <select id="tone-${script.script_id}">
              <option value="">Keep current</option>
              <option value="more formal-luxury">More formal / luxury</option>
              <option value="more casual-friendly">More casual / friendly</option>
              <option value="more urgent-scarcity">More urgent / scarcity</option>
              <option value="more aspirational-lifestyle">More aspirational / lifestyle</option>
            </select>
          </div>
          <div class="feedback-field">
            <label>Emphasis Shift</label>
            <select id="emphasis-${script.script_id}">
              <option value="">Keep current</option>
              <option value="focus on amenities">Focus on amenities</option>
              <option value="focus on location">Focus on location</option>
              <option value="focus on pricing-value">Focus on pricing / value</option>
              <option value="focus on lifestyle">Focus on lifestyle</option>
              <option value="focus on community">Focus on community</option>
            </select>
          </div>
          <div class="feedback-field">
            <label>Photo Emphasis</label>
            <select id="photo-${script.script_id}">
              <option value="">Keep current</option>
              <option value="pool-outdoor">Pool / outdoor spaces</option>
              <option value="kitchen-interiors">Kitchen / interiors</option>
              <option value="fitness center">Fitness center</option>
              <option value="building exterior">Building exterior</option>
              <option value="neighborhood">Neighborhood</option>
            </select>
          </div>
          <div class="feedback-field">
            <label>Call to Action</label>
            <select id="cta-${script.script_id}">
              <option value="">Keep current</option>
              <option value="schedule a tour">Schedule a tour</option>
              <option value="apply now">Apply now</option>
              <option value="learn more">Learn more</option>
              <option value="call us today">Call us today</option>
              <option value="see available units">See available units</option>
            </select>
          </div>
        </div>
        <div class="feedback-field" style="margin-bottom:16px;">
          <label>Additional Notes</label>
          <textarea id="notes-${script.script_id}" placeholder="e.g., Our residents skew younger — make it feel more energetic"></textarea>
        </div>
        <div class="feedback-actions">
          <button class="btn btn-primary ${portalData.revision_count >= portalData.max_revisions ? 'btn-disabled' : ''}"
            onclick="${portalData.revision_count >= portalData.max_revisions ? 'contactAM()' : `submitRevision('${script.script_id}')`}">
            ${portalData.revision_count >= portalData.max_revisions ? 'Contact your AM' : 'Submit Feedback'}
          </button>
          <span class="revision-counter"></span>
        </div>
      </div>
    `;

    return card;
  }

  // --- Actions ---

  window.toggleFeedback = function (scriptId) {
    const panel = document.getElementById(`feedback-${scriptId}`);
    panel.classList.toggle("active");
  };

  window.approveVariant = async function (scriptId) {
    const result = await apiPost("/api/approve", { variant_ids: [scriptId] });
    showToast(result.message || "Variant approved");
    loadPortalData();
  };

  window.approveAll = async function () {
    const result = await apiPost("/api/approve", { variant_ids: "all" });
    showToast(result.message || "All variants approved");
    loadPortalData();
  };

  window.submitRevision = async function (scriptId) {
    const body = {
      variant_script_id: scriptId,
      tone_shift: document.getElementById(`tone-${scriptId}`).value || null,
      emphasis_shift: document.getElementById(`emphasis-${scriptId}`).value || null,
      photo_emphasis: document.getElementById(`photo-${scriptId}`).value || null,
      cta_change: document.getElementById(`cta-${scriptId}`).value || null,
      free_text_notes: document.getElementById(`notes-${scriptId}`).value || "",
    };

    showToast("Submitting feedback — your revised creative will be ready in a few minutes...");
    const result = await apiPost("/api/revision", body);

    if (result.error) {
      showToast(result.message || result.error, true);
    } else {
      showToast("Revision complete! Refreshing...");
      setTimeout(() => loadPortalData(), 1500);
    }
  };

  window.contactAM = function () {
    window.location.href = "mailto:?subject=Additional%20Revisions%20Request";
  };

  // --- Budget Simulator ---

  function renderBudgetSimulator() {
    const snap = portalData.performance_snapshot;
    if (!snap || !snap.aggregate_cpl) return;

    const currentTier = portalData.package_tier;
    const tiers = { Starter: 2, Standard: 4, Premium: 6 };
    const currentVariants = tiers[currentTier] || 2;
    const nextTier = currentTier === "Starter" ? "Standard" : "Premium";
    const nextVariants = tiers[nextTier] || 4;

    const currentReach = snap.total_impressions || 0;
    const currentLeads = snap.total_leads || 0;
    const convRate = currentReach > 0 ? currentLeads / currentReach : 0;
    const cpl = snap.aggregate_cpl || 0;

    const nextReach = Math.round(currentReach * (nextVariants / currentVariants));
    const nextLeads = Math.round(nextReach * convRate);

    const boostReach = nextReach * 2;
    const boostLeads = Math.round(boostReach * convRate);

    const table = document.getElementById("simulator-table");
    table.innerHTML = `
      <thead>
        <tr>
          <th>Metric</th>
          <th>Current (${currentTier})</th>
          <th class="highlight">${nextTier}</th>
          <th>${nextTier} + 2x Budget</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Variants</td>
          <td>${currentVariants}</td>
          <td class="highlight">${nextVariants}</td>
          <td>${nextVariants}</td>
        </tr>
        <tr>
          <td>Projected Reach</td>
          <td>${currentReach.toLocaleString()}</td>
          <td class="highlight">${nextReach.toLocaleString()}</td>
          <td>${boostReach.toLocaleString()}</td>
        </tr>
        <tr>
          <td>Projected Leads</td>
          <td>${currentLeads.toLocaleString()}</td>
          <td class="highlight">${nextLeads.toLocaleString()}</td>
          <td>${boostLeads.toLocaleString()}</td>
        </tr>
        <tr>
          <td>Est. CPL</td>
          <td>$${cpl.toFixed(2)}</td>
          <td class="highlight">$${cpl.toFixed(2)}</td>
          <td>$${cpl.toFixed(2)}</td>
        </tr>
      </tbody>
    `;
  }

  window.submitUpsell = async function (tier) {
    const result = await apiPost("/api/upsell", { interested_tier: tier });
    showToast(result.message || "Interest submitted");
  };

  // --- Toast ---

  function showToast(msg, isError) {
    const toast = document.createElement("div");
    toast.style.cssText = `
      position:fixed;bottom:24px;left:50%;transform:translateX(-50%);
      background:${isError ? "#dc2626" : "#1a1a2e"};color:#fff;
      padding:12px 24px;border-radius:8px;font-size:14px;z-index:1000;
      box-shadow:0 4px 12px rgba(0,0,0,0.15);
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }

  // --- Boot ---

  document.addEventListener("DOMContentLoaded", loadPortalData);
})();
