const MAIN_SITE = "/main";

// The release is opened by hand on the server. The page asks every 30 seconds and opens the site once it is out.
async function checkRelease() {
  try {
    const response = await fetch("/api/release-status", { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json();
    if (data.released) window.location.assign(MAIN_SITE);
  } catch (error) {
    // The server is not reachable right now, the next check will try again.
  }
}

checkRelease();
setInterval(checkRelease, 30000);
