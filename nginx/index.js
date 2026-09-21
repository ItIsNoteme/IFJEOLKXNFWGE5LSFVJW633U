const MAIN_SITE = "/main";

const countdown = document.querySelector("#countdown");
const progressBar = document.querySelector("#progress-bar");
const status = document.querySelector("#status");
const restartButton = document.querySelector("#restart");
let timer;
let serverNow;
let releaseAt;
let startedAt;

function formatRemaining(milliseconds) {
  const totalSeconds = Math.max(Math.ceil(milliseconds / 1000), 0);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return `${days}d ${String(hours).padStart(2, "0")}h ${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}s`;
}

function startTimer() {
  clearInterval(timer);
  startedAt = Date.now();
  status.textContent = "Counting from server time...";

  timer = setInterval(() => {
    const currentServerTime = serverNow + (Date.now() - startedAt);
    const remaining = releaseAt - currentServerTime;
    countdown.textContent = formatRemaining(remaining);
    progressBar.style.width = `${Math.min(Math.max((currentServerTime - serverNow) / (releaseAt - serverNow) * 100, 0), 100)}%`;

    if (remaining <= 0) {
      clearInterval(timer);
      status.textContent = "Starting main site...";
      window.location.assign(MAIN_SITE);
    }
  }, 250);
}

async function loadServerTime() {
  try {
    const response = await fetch("/api/release-status", { cache: "no-store" });
    if (!response.ok) throw new Error("Server time unavailable");
    const data = await response.json();
    serverNow = Date.parse(data.server_time);
    releaseAt = Date.parse(data.release_time);
    if (data.released) {
      window.location.assign(MAIN_SITE);
      return;
    }
    startTimer();
  } catch (error) {
    clearInterval(timer);
    countdown.textContent = "--:--:--";
    status.textContent = "Server time unavailable. Timer is locked.";
  }
}

restartButton.addEventListener("click", loadServerTime);
loadServerTime();