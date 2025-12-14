// frontend/app.js

// Use the same origin where backend runs
const API_BASE_URL = window.location.origin;

const PAGE_SIZE = 50;

let users = [];
let userOffset = 0;
let isLoadingUsers = false;
let hasMoreUsers = true;
let currentUserId = null;
let currentView = "home";

document.addEventListener("DOMContentLoaded", () => {
  setupUserDropdown();
  setupViewTabs();
  setupClearHistoryButton();

  // Load users + initial recommendations
  fetchNextUsersPage().then(() => {
    if (users.length > 0) {
      selectUser(users[0]);
    } else {
      setStatus("No users with purchases found.", true);
    }
  });

  // Preload Product Page data
  loadProductPage();
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

/* ---------- view tabs (different "screens") ---------- */

function setupViewTabs() {
  const tabs = document.querySelectorAll(".view-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const view = tab.dataset.view;
      if (!view) return;
      showView(view);
    });
  });
  showView("home");
}

function showView(view) {
  currentView = view;
  const views = ["home", "product", "cart"];

  views.forEach((name) => {
    const section = $(name + "-view");
    if (section) {
      section.style.display = name === view ? "block" : "none";
    }
    const tab = document.querySelector(`.view-tab[data-view="${name}"]`);
    if (tab) {
      if (name === view) tab.classList.add("active");
      else tab.classList.remove("active");
    }
  });

  if (view === "product") {
    // refresh product page when we switch to it
    loadProductPage();
  }
}

/* ---------- clear history button ---------- */

function setupClearHistoryButton() {
  const btn = $("clear-history-btn");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    if (!currentUserId) return;

    const confirmed = window.confirm(
      "This will clear the purchase history for this customer in the demo and remove their personalized recommendations. Continue?"
    );
    if (!confirmed) return;

    try {
      setStatus("Clearing purchase history...");
      const url = `${API_BASE_URL}/api/users/${encodeURIComponent(
        currentUserId
      )}/history`;
      const resp = await fetch(url, { method: "DELETE" });

      if (!resp.ok && resp.status !== 204) {
        throw new Error(`History HTTP ${resp.status}`);
      }

      // Reload recommendations for this user (now cold-start)
      await loadRecommendationsForUser(currentUserId);

      // Update label in dropdown
      const opt = document.querySelector(
        `.user-option[data-user-id="${currentUserId}"]`
      );
      if (opt) {
        const meta = opt.querySelector(".user-meta");
        if (meta) meta.textContent = "history cleared";
      }

      setStatus(
        "Purchase history cleared for this customer. No personalized recommendations available anymore."
      );
    } catch (err) {
      console.error(err);
      setStatus("Failed to clear purchase history.", true);
    }
  });
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
    toggle.textContent = "Loading users…";
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
  setStatus(`Loading recommendations for customer ${userId}…`);
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
    setStatus(
      "Failed to load recommendations. See console for details.",
      true
    );
  }
}

function renderRecommendations(data) {
  const boughtDescriptions = data.bought_descriptions || [];
  const recs = data.recommendations || [];

  const fbt = recs.slice(0, 4);
  const cartRecs = recs.slice(4, 8);
  const personal = recs.slice(8);

  // history for HOME view
  renderHistory(boughtDescriptions);

  // HOME view blocks
  renderProductGrid("fbt-grid", fbt, "Frequently bought together");
  renderProductGrid("personal-grid", personal, "Personalized recommendation");

  // CART view blocks
  renderCart(boughtDescriptions, cartRecs);
}

/* --- previous purchases (HOME) --- */
function renderHistory(boughtDescriptions) {
  const container = $("history-list");
  if (!container) return;

  container.innerHTML = "";

  if (!boughtDescriptions || boughtDescriptions.length === 0) {
    container.innerHTML =
      '<p class="empty-text">No purchase history for this customer yet.</p>';
    return;
  }

  boughtDescriptions.slice(0, 20).forEach((desc) => {
    const div = document.createElement("div");
    div.className = "history-item";
    div.textContent = escapeHtml(desc);
    container.appendChild(div);
  });
}

/* --- product grids + cart --- */

function renderProductGrid(containerId, items, badgeLabel) {
  const container = $(containerId);
  if (!container) return;

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

  if (boughtContainer) boughtContainer.innerHTML = "";
  if (recsContainer) recsContainer.innerHTML = "";

  if (boughtContainer) {
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
  }

  if (recsContainer) {
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
}

/* ---------- Product Page: random product + FBT ---------- */

async function loadProductPage() {
  try {
    const url = `${API_BASE_URL}/api/products/random?top_n=8`;
    const resp = await fetch(url);
    if (!resp.ok) {
      console.error("Product page HTTP", resp.status);
      return;
    }

    const data = await resp.json();
    const product = data.product;
    const fbtItems = data.frequently_bought_together || [];

    renderProductPage(product, fbtItems);
  } catch (err) {
    console.error("Error loading product page:", err);
  }
}

function renderProductPage(product, fbtItems) {
  const titleEl = $("pp-title");
  const descEl = $("pp-description");
  const idEl = $("pp-product-id");
  const fbtContainer = $("pp-fbt-grid");

  if (!titleEl || !descEl || !idEl || !fbtContainer) {
    return;
  }

  const title = escapeHtml(
    product?.description || product?.product_id || "Product"
  );
  titleEl.textContent = title;

  descEl.textContent = "Random product from the Online Retail dataset.";
  idEl.textContent = `Product ID: ${escapeHtml(product.product_id)}`;

  fbtContainer.innerHTML = "";

  if (!fbtItems.length) {
    fbtContainer.innerHTML =
      '<p class="empty-text">No related products found.</p>';
    return;
  }

  fbtItems.forEach((item) => {
    const card = document.createElement("div");
    card.className = "product-card";

    const title = escapeHtml(item.description || item.product_id);
    const score =
      typeof item.score === "number" ? item.score.toFixed(3) : "";

    card.innerHTML = `
      <div class="product-image">
        <div class="recommendation-badge badge-fbt">Frequently bought together</div>
        ${score ? `<div class="score-badge">score: ${score}</div>` : ""}
      </div>
      <div class="product-info">
        <div class="product-title">${title}</div>
        <div class="product-description">Product ID: ${escapeHtml(
          item.product_id
        )}</div>
      </div>
    `;

    fbtContainer.appendChild(card);
  });
}
