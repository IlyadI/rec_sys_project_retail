// frontend/app.js

// бьёмся в тот же origin, где крутится backend
const API_BASE_URL = window.location.origin;

const PAGE_SIZE = 50;

let users = [];
let userOffset = 0;
let isLoadingUsers = false;
let hasMoreUsers = true;
let currentUserId = null;

document.addEventListener("DOMContentLoaded", () => {
  setupUserDropdown();
  fetchNextUsersPage().then(() => {
    if (users.length > 0) {
      selectUser(users[0]);
    } else {
      setStatus("No users with purchases found.", true);
    }
  });
});

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setStatus(text, isError = false) {
  const bar = $("status-bar");
  const label = $("status-text");
  if (!bar) return;
  if (!text) {
    bar.style.display = "none";
    return;
  }
  label.textContent = text;
  bar.className = "status-bar " + (isError ? "error" : "info");
  bar.style.display = "flex";
}

/* ---------- user dropdown ---------- */

function setupUserDropdown() {
  const toggle = $("user-select-toggle");
  const optionsEl = $("user-options");

  toggle.addEventListener("click", (e) => {
    e.stopPropagation();
    optionsEl.classList.toggle("open");
  });

  optionsEl.addEventListener("scroll", () => {
    if (
      optionsEl.scrollTop + optionsEl.clientHeight >=
      optionsEl.scrollHeight - 40
    ) {
      fetchNextUsersPage();
    }
  });

  document.addEventListener("click", (e) => {
    if (!optionsEl.contains(e.target) && e.target !== toggle) {
      optionsEl.classList.remove("open");
    }
  });
}

async function fetchNextUsersPage() {
  if (isLoadingUsers || !hasMoreUsers) return;

  isLoadingUsers = true;
  const toggle = $("user-select-toggle");
  if (!currentUserId) {
    toggle.textContent = "Loading users...";
  }

  try {
    const url = `${API_BASE_URL}/api/users?limit=${PAGE_SIZE}&offset=${userOffset}`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`Users HTTP ${resp.status}`);

    const data = await resp.json();
    const pageUsers = Array.isArray(data.users) ? data.users : data;

    if (!Array.isArray(pageUsers) || pageUsers.length === 0) {
      hasMoreUsers = false;
      if (users.length === 0) {
        toggle.textContent = "No users found";
      }
      return;
    }

    users = users.concat(pageUsers);
    userOffset += pageUsers.length;

    renderUserOptions(pageUsers);

    if (data.has_more === false || pageUsers.length < PAGE_SIZE) {
      hasMoreUsers = false;
    }

    if (!currentUserId && users.length > 0) {
      toggle.textContent = `Customer #${users[0]}`;
    }
  } catch (err) {
    console.error(err);
    $("user-select-toggle").textContent = "Error loading users";
    setStatus("Failed to load users list.", true);
  } finally {
    isLoadingUsers = false;
  }
}

function renderUserOptions(newUsers) {
  const optionsEl = $("user-options");
  newUsers.forEach((id) => {
    const opt = document.createElement("div");
    opt.className = "user-option";
    opt.innerHTML = `
      <span class="user-id">Customer #${id}</span>
      <span class="user-meta">has purchases</span>
    `;
    opt.dataset.userId = id;
    opt.addEventListener("click", () => {
      $("user-options").classList.remove("open");
      selectUser(id);
    });
    optionsEl.appendChild(opt);
  });
}

async function selectUser(userId) {
  currentUserId = userId;
  $("user-select-toggle").textContent = `Customer #${userId}`;
  $("user-label").textContent = `Customer #${userId}`;
  $("page-user-id").textContent = userId;
  $("user-avatar").textContent = String(userId).slice(-2);
  await loadRecommendationsForUser(userId);
}

/* ---------- recommendations ---------- */

async function loadRecommendationsForUser(userId) {
  setStatus(`Loading recommendations for customer ${userId}...`);
  try {
    const url = `${API_BASE_URL}/api/users/${encodeURIComponent(
      userId
    )}/recommendations?top_n=12`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`Recommendations HTTP ${resp.status}`);
    const data = await resp.json();
    renderRecommendations(data);
    setStatus("");
  } catch (err) {
    console.error(err);
    setStatus("Failed to load recommendations. See console for details.", true);
  }
}

function renderRecommendations(data) {
  const boughtDescriptions = data.bought_descriptions || [];
  const recs = data.recommendations || [];

  const fbt = recs.slice(0, 4);
  const cartRecs = recs.slice(4, 8);
  const personal = recs.slice(8);

  // новый блок — история покупок
  renderHistory(boughtDescriptions);

  renderProductGrid("fbt-grid", fbt, "Frequently bought together");
  renderCart(boughtDescriptions, cartRecs);
  renderProductGrid("personal-grid", personal, "Personalized recommendation");
}

/* --- NEW: previous purchases --- */
function renderHistory(boughtDescriptions) {
  const container = $("history-list");
  if (!container) return;

  container.innerHTML = "";

  if (!boughtDescriptions || boughtDescriptions.length === 0) {
    container.innerHTML =
      '<p class="empty-text">No purchase history for this customer yet.</p>';
    return;
  }

  boughtDescriptions.slice(0, 20).forEach((desc, idx) => {
    const div = document.createElement("div");
    div.className = "history-item";
    div.textContent = escapeHtml(desc);
    container.appendChild(div);
  });
}

/* --- product grids + cart --- */

function renderProductGrid(containerId, items, badgeLabel) {
  const container = $(containerId);
  container.innerHTML = "";

  if (!items || items.length === 0) {
    container.innerHTML =
      '<p class="empty-text">No recommendations available yet.</p>';
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "product-card";

    const title = escapeHtml(item.description || item.product_id);
    const explanation = escapeHtml(
      item.explanation || "No explanation from the model."
    );
    const score =
      typeof item.score === "number" ? item.score.toFixed(3) : "";

    card.innerHTML = `
      <div class="product-image">
        <div class="recommendation-badge">${badgeLabel}</div>
        ${score ? `<div class="score-badge">score: ${score}</div>` : ""}
      </div>
      <div class="product-info">
        <div class="product-title">${title}</div>
        <div class="product-description">Product ID: ${escapeHtml(
          item.product_id
        )}</div>
        <div class="tooltip">
          <span>Why recommended?</span>
          <span class="tooltip-icon">?</span>
          <span class="tooltip-text">${explanation}</span>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

function renderCart(boughtDescriptions, cartRecs) {
  const boughtContainer = $("cart-bought-items");
  const recsContainer = $("cart-recs");

  boughtContainer.innerHTML = "";
  recsContainer.innerHTML = "";

  if (!boughtDescriptions || boughtDescriptions.length === 0) {
    boughtContainer.innerHTML =
      '<p class="empty-text">No historical purchases found for this user.</p>';
  } else {
    boughtDescriptions.slice(0, 5).forEach((desc, idx) => {
      const div = document.createElement("div");
      div.className = "cart-item";
      div.innerHTML = `
        <div class="cart-item-icon">${idx + 1}</div>
        <div>
          <div class="cart-item-title">${escapeHtml(desc)}</div>
          <div class="cart-item-meta">Previously bought item</div>
        </div>
      `;
      boughtContainer.appendChild(div);
    });
  }

  if (!cartRecs || cartRecs.length === 0) {
    recsContainer.innerHTML =
      '<p class="empty-text">No cart-aware recommendations for this user.</p>';
  } else {
    cartRecs.forEach((item) => {
      const div = document.createElement("div");
      div.className = "rec-card";
      const title = escapeHtml(item.description || item.product_id);
      const explanation = escapeHtml(
        item.explanation || "No explanation from the model."
      );
      div.innerHTML = `
        <h4>${title}</h4>
        <p>Product ID: ${escapeHtml(item.product_id)}</p>
        <div class="tooltip" style="margin-top:0.4rem;">
          <span>Why recommended?</span>
          <span class="tooltip-icon">?</span>
          <span class="tooltip-text">${explanation}</span>
        </div>
      `;
      recsContainer.appendChild(div);
    });
  }
}