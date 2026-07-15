const collapseBtn = document.getElementById("collapseBtn");
const restoreBtn = document.getElementById("restoreBtn");

function setSidebarCollapsed(collapsed) {
  document.body.classList.toggle("sidebar-collapsed", collapsed);
  localStorage.setItem("etsytools.sidebarCollapsed", collapsed ? "1" : "0");
}

if (localStorage.getItem("etsytools.sidebarCollapsed") === "1") {
  setSidebarCollapsed(true);
}

collapseBtn?.addEventListener("click", () => setSidebarCollapsed(true));
restoreBtn?.addEventListener("click", () => setSidebarCollapsed(false));

document.querySelectorAll("[data-copy-target]").forEach((button) => {
  button.addEventListener("click", async () => {
    const key = button.getAttribute("data-copy-target");
    const source = document.querySelector(`[data-copy-source="${key}"]`);
    if (!source) return;

    const value = source.value ?? source.textContent ?? "";
    await navigator.clipboard.writeText(value);
    const original = button.textContent;
    button.textContent = "Copied";
    setTimeout(() => {
      button.textContent = original;
    }, 1200);
  });
});

document.querySelectorAll("form").forEach((form) => {
  form.addEventListener("submit", () => {
    if (form.checkValidity()) {
      const overlay = document.getElementById("loadingOverlay");
      if (overlay) {
        overlay.style.display = "flex";
        const button = form.querySelector("button[type='submit']");
        const msgEl = document.getElementById("loadingMessage");
        if (button && msgEl) {
          msgEl.textContent = button.getAttribute("data-loading-msg") ?? "Processing, please wait...";
        }
      }
    }
  });
});

