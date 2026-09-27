/* ============================================================
   Student Project Management Portal — Modern SaaS JavaScript
   ============================================================ */

"use strict";

// ---------- CSRF Token Helper ----------
function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || "";
}

// ---------- Toast Notification System ----------
function showToast(message, type = "success") {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const icons = {
    success: "✓",
    danger: "✕",
    info: "ℹ",
    warning: "⚠",
  };

  const toast = document.createElement("div");
  toast.className = `toast-item toast-${type}`;
  toast.innerHTML = `
    <span style="font-weight:700;">${icons[type] || "•"}</span>
    <span style="flex:1;">${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = "opacity 0.4s, transform 0.4s";
    toast.style.opacity = "0";
    toast.style.transform = "translateY(8px)";
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}

// ---------- Theme Toggle (Dark / Light) ----------
function initTheme() {
  const savedTheme = localStorage.getItem("sp_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeIcon(savedTheme);

  document.querySelectorAll(".theme-toggle-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("sp_theme", next);
      updateThemeIcon(next);
      showToast(`Switched to ${next} theme`, "info");

      // Update Chart.js if present
      if (window._progressChart) {
        window._progressChart.update();
      }
      if (window._statusChart) {
        window._statusChart.update();
      }
    });
  });
}

function updateThemeIcon(theme) {
  document.querySelectorAll(".theme-toggle-btn").forEach(btn => {
    btn.innerHTML = theme === "dark" ? "☀️" : "🌙";
    btn.title = theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode";
  });
}

// ---------- Tabs Switcher ----------
function initTabs() {
  document.querySelectorAll(".tabs-nav").forEach(nav => {
    const buttons = nav.querySelectorAll(".tab-btn");
    buttons.forEach(btn => {
      btn.addEventListener("click", () => {
        const targetId = btn.dataset.tab;
        buttons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        const container = nav.closest(".tabbed-container") || document;
        container.querySelectorAll(".tab-pane").forEach(pane => {
          if (pane.id === targetId) {
            pane.classList.add("active");
          } else {
            pane.classList.remove("active");
          }
        });
      });
    });
  });
}

// ---------- Interactive Kanban Drag & Drop ----------
function initKanban() {
  const cards = document.querySelectorAll(".kanban-card");
  const columns = document.querySelectorAll(".kanban-col");

  if (!cards.length || !columns.length) return;

  cards.forEach(card => {
    card.setAttribute("draggable", "true");

    card.addEventListener("dragstart", e => {
      card.classList.add("dragging");
      e.dataTransfer.setData("text/plain", card.dataset.taskId);
      e.dataTransfer.effectAllowed = "move";
    });

    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      columns.forEach(col => col.classList.remove("drag-over"));
    });
  });

  columns.forEach(col => {
    col.addEventListener("dragover", e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      col.classList.add("drag-over");
    });

    col.addEventListener("dragleave", e => {
      if (!col.contains(e.relatedTarget)) {
        col.classList.remove("drag-over");
      }
    });

    col.addEventListener("drop", async e => {
      e.preventDefault();
      col.classList.remove("drag-over");

      const taskId = e.dataTransfer.getData("text/plain");
      const targetCard = document.querySelector(`.kanban-card[data-task-id="${taskId}"]`);
      const newStatus = col.dataset.status;

      if (!targetCard || !newStatus) return;

      const cardList = col.querySelector(".kanban-card-list");
      if (cardList && targetCard.parentElement !== cardList) {
        // Move DOM element optimistically
        cardList.appendChild(targetCard);
        updateKanbanCounts();

        // Update badge
        const badge = targetCard.querySelector(".status-badge");
        if (badge) {
          badge.className = `badge badge-${newStatus} status-badge`;
          badge.textContent = newStatus.replace("_", " ");
        }

        // Call backend API
        try {
          const resp = await fetch(`/tasks/${taskId}/kanban-move`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({ status: newStatus }),
          });

          if (resp.ok) {
            const data = await resp.json();
            showToast(`Task moved to ${newStatus.replace("_", " ")}`, "success");
            if (data.progress !== undefined && window._progressChart) {
              window._progressChart.data.datasets[0].data = [data.progress, 100 - data.progress];
              window._progressChart.update();
            }
            const progBar = document.getElementById("project-progress-bar");
            if (progBar && data.progress !== undefined) {
              progBar.style.width = `${data.progress}%`;
            }
            const progText = document.getElementById("project-progress-text");
            if (progText && data.progress !== undefined) {
              progText.textContent = `${data.progress}%`;
            }
          } else {
            showToast("Failed to update task status", "danger");
            setTimeout(() => location.reload(), 800);
          }
        } catch (err) {
          showToast("Network error moving task", "danger");
        }
      }
    });
  });
}

function updateKanbanCounts() {
  document.querySelectorAll(".kanban-col").forEach(col => {
    const count = col.querySelectorAll(".kanban-card").length;
    const pill = col.querySelector(".kanban-count-pill");
    if (pill) pill.textContent = count;
  });
}

// ---------- Command Palette / Quick Search (Ctrl+K) ----------
function initQuickSearch() {
  const modal = document.getElementById("quick-search-modal");
  const input = document.getElementById("quick-search-input");
  const resultsContainer = document.getElementById("quick-search-results");

  if (!modal || !input) return;

  function openSearch() {
    modal.classList.add("open");
    input.value = "";
    if (resultsContainer) resultsContainer.innerHTML = '<div style="padding:1rem;color:var(--text-muted);font-size:.85rem;text-align:center;">Type to search projects, tasks, and groups...</div>';
    setTimeout(() => input.focus(), 50);
  }

  function closeSearch() {
    modal.classList.remove("open");
  }

  // Open triggers
  document.querySelectorAll(".quick-search-btn").forEach(btn => {
    btn.addEventListener("click", openSearch);
  });

  // Keyboard shortcut Ctrl+K / Cmd+K
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (modal.classList.contains("open")) {
        closeSearch();
      } else {
        openSearch();
      }
    } else if (e.key === "Escape" && modal.classList.contains("open")) {
      closeSearch();
    }
  });

  modal.addEventListener("click", e => {
    if (e.target === modal) closeSearch();
  });

  // Debounced search
  let debounceTimeout = null;
  input.addEventListener("input", () => {
    clearTimeout(debounceTimeout);
    const q = input.value.trim();
    if (q.length < 2) {
      if (resultsContainer) resultsContainer.innerHTML = '<div style="padding:1rem;color:var(--text-muted);font-size:.85rem;text-align:center;">Type at least 2 characters to search...</div>';
      return;
    }

    debounceTimeout = setTimeout(async () => {
      try {
        const resp = await fetch(`/api/quick-search?q=${encodeURIComponent(q)}`);
        if (!resp.ok) return;
        const data = await resp.json();

        if (!data.results || data.results.length === 0) {
          resultsContainer.innerHTML = '<div style="padding:1.5rem;color:var(--text-muted);font-size:.88rem;text-align:center;">No matching items found.</div>';
          return;
        }

        resultsContainer.innerHTML = data.results.map(r => `
          <a href="${r.url}" class="search-result-item">
            <span class="search-result-icon">${r.icon}</span>
            <div class="search-result-info">
              <div class="search-result-title">${r.title}</div>
              <div class="search-result-sub">${r.type} · ${r.subtitle}</div>
            </div>
            <span style="font-size:.8rem;color:var(--text-muted);">↵</span>
          </a>
        `).join("");
      } catch (_) {}
    }, 250);
  });
}

// ---------- Mobile Sidebar ----------
function initSidebar() {
  const sidebar = document.querySelector(".sidebar");
  const hamburger = document.querySelector(".hamburger");
  const overlay = document.querySelector(".sidebar-overlay");

  if (hamburger) {
    hamburger.addEventListener("click", () => {
      sidebar?.classList.toggle("open");
      overlay?.classList.toggle("open");
    });
  }
  if (overlay) {
    overlay.addEventListener("click", () => {
      sidebar?.classList.remove("open");
      overlay?.classList.remove("open");
    });
  }
}

// ---------- Confirm Modal ----------
function openConfirmModal(formId, message) {
  const modal = document.getElementById("confirm-modal");
  const body = document.getElementById("confirm-modal-body");
  const confirmBtn = document.getElementById("confirm-modal-ok");
  if (!modal) return;

  body.textContent = message || "Are you sure you want to proceed?";
  modal.classList.add("open");

  confirmBtn.onclick = () => {
    modal.classList.remove("open");
    document.getElementById(formId)?.submit();
  };
}

function initConfirmModal() {
  const modal = document.getElementById("confirm-modal");
  if (!modal) return;

  document.getElementById("confirm-modal-cancel")?.addEventListener("click", () => {
    modal.classList.remove("open");
  });
  modal.addEventListener("click", e => {
    if (e.target === modal) modal.classList.remove("open");
  });
}

// ---------- Flash Auto Dismiss ----------
function initFlashDismiss() {
  document.querySelectorAll(".alert-close").forEach(btn => {
    btn.addEventListener("click", () => {
      btn.closest(".alert")?.remove();
    });
  });

  setTimeout(() => {
    document.querySelectorAll(".alert-success").forEach(el => {
      el.style.transition = "opacity 0.5s";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 500);
    });
  }, 4000);
}

// ---------- Tech Tag Input Helper ----------
function initTagInput() {
  const tagInput = document.getElementById("tech-tag-input");
  const tagHidden = document.getElementById("tech_tags");
  const tagDisplay = document.getElementById("tag-display");

  if (!tagInput || !tagHidden) return;

  const existing = (tagHidden.value || "").split(",").map(t => t.trim()).filter(Boolean);
  existing.forEach(t => renderTag(t));

  tagInput.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const val = tagInput.value.trim().replace(/,$/, "");
      if (val) {
        addTag(val);
        tagInput.value = "";
      }
    }
  });

  function addTag(text) {
    const tags = currentTags();
    if (!tags.includes(text)) {
      tags.push(text);
      tagHidden.value = tags.join(",");
      renderTag(text);
    }
  }

  function renderTag(text) {
    if (!tagDisplay) return;
    const span = document.createElement("span");
    span.className = "tag-chip";
    span.textContent = text;
    const rm = document.createElement("button");
    rm.type = "button";
    rm.style.cssText = "background:none;border:none;cursor:pointer;margin-left:.35rem;color:inherit;font-weight:700;";
    rm.textContent = "×";
    rm.addEventListener("click", () => {
      span.remove();
      const tags = currentTags().filter(t => t !== text);
      tagHidden.value = tags.join(",");
    });
    span.appendChild(rm);
    tagDisplay.appendChild(span);
  }

  function currentTags() {
    return (tagHidden.value || "").split(",").map(t => t.trim()).filter(Boolean);
  }
}

// ---------- Image Preview ----------
function initImagePreview() {
  const fileInput = document.getElementById("group-image-input");
  const preview = document.getElementById("group-image-preview");
  if (!fileInput || !preview) return;

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
      preview.src = e.target.result;
      preview.style.display = "block";
    };
    reader.readAsDataURL(file);
  });
}

// ---------- Main Initialization ----------
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initSidebar();
  initTabs();
  initKanban();
  initQuickSearch();
  initConfirmModal();
  initFlashDismiss();
  initTagInput();
  initImagePreview();
});
