const root = document.documentElement;
const header = document.querySelector("[data-header]");
const themeToggle = document.querySelector("[data-theme-toggle]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const mobileMenu = document.querySelector("[data-mobile-menu]");
const copyButton = document.querySelector("[data-copy-email]");
const copyLabel = document.querySelector("[data-copy-label]");
const toast = document.querySelector("[data-toast]");

const storedTheme = localStorage.getItem("cv-theme");
const preferredTheme = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
const initialTheme = storedTheme || preferredTheme;

function setTheme(theme) {
  root.dataset.theme = theme;
  themeToggle?.setAttribute("aria-label", theme === "dark" ? "Use light theme" : "Use dark theme");
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#0a0d10" : "#f3f0e8");
}

setTheme(initialTheme);

themeToggle?.addEventListener("click", () => {
  const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
  setTheme(nextTheme);
  localStorage.setItem("cv-theme", nextTheme);
});

function updateHeader() {
  header?.classList.toggle("is-scrolled", window.scrollY > 12);
}

updateHeader();
window.addEventListener("scroll", updateHeader, { passive: true });

function openMenu() {
  if (!mobileMenu || !menuToggle) return;
  mobileMenu.hidden = false;
  requestAnimationFrame(() => mobileMenu.classList.add("is-open"));
  menuToggle.setAttribute("aria-expanded", "true");
  document.body.classList.add("menu-open");
}

function closeMenu() {
  if (!mobileMenu || !menuToggle) return;
  mobileMenu.classList.remove("is-open");
  menuToggle.setAttribute("aria-expanded", "false");
  document.body.classList.remove("menu-open");
  window.setTimeout(() => {
    if (!mobileMenu.classList.contains("is-open")) mobileMenu.hidden = true;
  }, 180);
}

menuToggle?.addEventListener("click", () => {
  const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
  isOpen ? closeMenu() : openMenu();
});

mobileMenu?.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && menuToggle?.getAttribute("aria-expanded") === "true") {
    closeMenu();
    menuToggle.focus();
  }
});

copyButton?.addEventListener("click", () => {
  const email = copyButton.dataset.email;
  if (!email) return;

  const showCopiedState = () => {
    copyLabel.textContent = "Copied";
    toast?.classList.add("is-visible");
    window.setTimeout(() => toast?.classList.remove("is-visible"), 2800);
    window.setTimeout(() => (copyLabel.textContent = "Copy email"), 3200);
  };

  const fallback = document.createElement("textarea");
  fallback.value = email;
  fallback.setAttribute("readonly", "");
  fallback.style.position = "fixed";
  fallback.style.opacity = "0";
  document.body.appendChild(fallback);
  fallback.focus();
  fallback.select();
  const copied = document.execCommand("copy");
  fallback.remove();

  if (copied) {
    showCopiedState();
    return;
  }

  navigator.clipboard?.writeText(email).then(showCopiedState).catch(() => {});
});

document.querySelector("[data-year]").textContent = String(new Date().getFullYear());
