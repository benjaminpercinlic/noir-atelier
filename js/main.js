(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const veil = document.querySelector("[data-veil]");
  const lockup = document.querySelector("[data-lockup]");
  const stage = document.querySelector(".stage");
  const video = document.querySelector("[data-intro]");

  const reveal = () => {
    if (veil) veil.classList.add("is-gone");
    if (lockup) lockup.classList.add("is-in");
  };

  const startWithoutVideo = () => {
    if (reduce) reveal();
    else window.setTimeout(reveal, 380);
  };

  const tryIntroVideo = async () => {
    if (!video || reduce) {
      startWithoutVideo();
      return;
    }

    const source = video.querySelector("source");
    if (!source?.getAttribute("src")) {
      startWithoutVideo();
      return;
    }

    try {
      // Probe: if file missing, browser errors — fall back to poster
      await new Promise((resolve, reject) => {
        const onReady = () => {
          cleanup();
          resolve();
        };
        const onFail = () => {
          cleanup();
          reject(new Error("intro unavailable"));
        };
        const cleanup = () => {
          video.removeEventListener("loadeddata", onReady);
          video.removeEventListener("error", onFail);
          source.removeEventListener("error", onFail);
        };
        video.addEventListener("loadeddata", onReady, { once: true });
        video.addEventListener("error", onFail, { once: true });
        source.addEventListener("error", onFail, { once: true });
        video.load();
        // If already cached
        if (video.readyState >= 2) onReady();
      });

      stage?.classList.add("has-video");
      video.classList.add("is-on");
      video.currentTime = 0;
      await video.play();

      // Show brand after a beat into the clip
      window.setTimeout(reveal, 900);

      video.addEventListener(
        "ended",
        () => {
          // Keep last frame under overlay; brand already visible
        },
        { once: true }
      );
    } catch {
      startWithoutVideo();
    }
  };

  tryIntroVideo();
})();
