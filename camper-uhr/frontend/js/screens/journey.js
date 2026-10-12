// Reuse the approved renderer in an isolated same-origin frame.
function createJourneyScreen() {
  const element = document.createElement("div");
  element.className = "screen";
  const frame = document.createElement("iframe");
  frame.title = "Fahrten · Traccar";
  frame.style.cssText = "width:100%;height:100%;border:0;pointer-events:none";
  let ready = false, checked = 0;
  const receive = event => {
    if (event.origin !== location.origin || event.source !== frame.contentWindow
        || event.data?.type !== "camper-journey-state") return;
    ready = event.data.available === true;
    checked = Date.now();
  };
  const active = value => frame.contentWindow?.postMessage({type:"camper-journey-active", active:value}, location.origin);
  window.addEventListener("message", receive);
  frame.src = "/journey?embedded=1";
  element.appendChild(frame);
  return {
    element,
    isAvailable() { return ready && Date.now()-checked < 20000; },
    onMount() { active(true); },
    onUnmount() { active(false); },
    onDispose() { window.removeEventListener("message", receive); },
  };
}
