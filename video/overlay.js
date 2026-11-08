// Video overlay injected into the control tower by video/record.py.
// Exposes window.V with caption / spotlight / zoom / card / clear. Nothing here ships with the app.
(() => {
  const css = `
  #v-cap { position: fixed; left: 50%; bottom: 34px; transform: translateX(-50%); z-index: 2000;
    max-width: 1500px; padding: 18px 30px 16px; background: rgba(11,2,33,.94); border: 3px solid #ff2a6d;
    box-shadow: 0 0 0 3px #0b0221, 0 0 28px rgba(255,42,109,.55); font-family: "Press Start 2P", monospace;
    font-size: 26px; line-height: 1.45; color: #fff; text-align: center; letter-spacing: 1px;
    transition: opacity .25s, transform .25s; }
  #v-cap .k { display: block; font-size: 13px; color: #05d9e8; margin-bottom: 10px; letter-spacing: 3px; }
  #v-cap.off { opacity: 0; transform: translateX(-50%) translateY(14px); }
  .app.v-zoomable { transform-origin: 0 0; transition: transform .9s cubic-bezier(.65,0,.35,1); position: relative; }
  #v-spot { position: absolute; z-index: 1500; pointer-events: none; border: 3px solid #f9c80e;
    box-shadow: 0 0 0 9999px rgba(5,0,18,.72), 0 0 24px #f9c80e; transition: all .6s ease; }
  #v-card { position: fixed; inset: 0; z-index: 1800; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 34px; background: rgba(8,1,26,.86);
    font-family: "Press Start 2P", monospace; color: #fff; text-align: center; transition: opacity .5s; }
  #v-card.off { opacity: 0; pointer-events: none; }
  #v-card h1 { font-size: 64px; margin: 0; letter-spacing: 6px; text-shadow: 0 0 22px #ff2a6d; }
  #v-card h1 b { color: #ff2a6d; }
  #v-card h2 { font-size: 30px; margin: 0; color: #f9c80e; letter-spacing: 2px; }
  #v-card .row { display: flex; gap: 28px; }
  #v-card .st { border: 3px solid #05d9e8; padding: 22px 26px; min-width: 260px; background: #140838;
    box-shadow: 0 0 22px rgba(5,217,232,.4); }
  #v-card .st.m { border-color: #ff2a6d; box-shadow: 0 0 22px rgba(255,42,109,.4); }
  #v-card .st.g { border-color: #39ff14; box-shadow: 0 0 22px rgba(57,255,20,.35); }
  #v-card .st b { display: block; font-size: 52px; margin-bottom: 16px; }
  #v-card .st span { font-size: 15px; color: #8b84bf; letter-spacing: 1px; }
  #v-card p { font-family: "VT323", monospace; font-size: 40px; margin: 0; color: #e9e6ff; }
  #v-card .url { font-size: 22px; color: #05d9e8; }
  `;
  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  const cap = Object.assign(document.createElement("div"), { id: "v-cap", className: "off" });
  const card = Object.assign(document.createElement("div"), { id: "v-card", className: "off" });
  document.body.append(cap, card);

  const app = () => document.querySelector(".app");
  const panel = (title) => [...document.querySelectorAll("section.win")]
    .find((s) => (s.getAttribute("aria-label") || s.querySelector(".titlebar span")?.textContent || "").startsWith(title))
    || [...document.querySelectorAll("section.win")].find((s) => s.querySelector(".titlebar")?.textContent.includes(title));
  let scale = 1;

  // Panel rect in untransformed .app coordinates (offset* ignore CSS transforms, so this is
  // correct even mid-zoom-transition).
  const rectOf = (title) => {
    const el = panel(title), a = app();
    if (!el || !a) return null;
    a.classList.add("v-zoomable");
    let x = 0, y = 0, n = el;
    while (n && n !== a) { x += n.offsetLeft; y += n.offsetTop; n = n.offsetParent; }
    return { x, y, w: el.offsetWidth, h: el.offsetHeight };
  };

  window.V = {
    caption(text, kicker) {
      cap.innerHTML = (kicker ? `<span class="k">${kicker}</span>` : "") + text;
      cap.className = "";
    },
    hideCaption() { cap.className = "off"; },
    spotlight(title, pad = 6) {
      const a = app(), r = rectOf(title);
      if (!a || !r) return false;
      a.classList.add("v-zoomable");
      let s = document.getElementById("v-spot");
      if (!s) { s = document.createElement("div"); s.id = "v-spot"; a.appendChild(s); }
      Object.assign(s.style, { left: r.x - pad + "px", top: r.y - pad + "px", width: r.w + pad * 2 + "px", height: r.h + pad * 2 + "px" });
      return true;
    },
    unspot() { document.getElementById("v-spot")?.remove(); },
    zoom(title, s = 1.5, bias = 0) {
      const a = app(), r = rectOf(title);
      if (!a || !r) return false;
      a.classList.add("v-zoomable");
      const W = innerWidth, H = innerHeight - 140; // keep the zoomed panel above the caption bar
      const cx = r.x + r.w / 2, cy = r.y + r.h / 2 + bias;
      const tx = Math.min(0, Math.max(innerWidth - innerWidth * s, W / 2 - cx * s));
      const ty = Math.min(0, Math.max(innerHeight - innerHeight * s, H / 2 - cy * s));
      a.style.transform = `translate(${tx}px, ${ty}px) scale(${s})`;
      scale = s;
      return true;
    },
    unzoom() { const a = app(); if (a) a.style.transform = ""; scale = 1; },
    card(html) { card.innerHTML = html; card.className = ""; },
    uncard() { card.className = "off"; },
    clear() { this.unspot(); this.unzoom(); this.uncard(); },
    // Solid green full-screen frame; build.py finds it to sync footage with narration.
    sync(on) {
      let m = document.getElementById("v-sync");
      if (on && !m) {
        m = document.createElement("div"); m.id = "v-sync";
        Object.assign(m.style, { position: "fixed", inset: 0, zIndex: 9999, background: "#00ff00" });
        document.body.appendChild(m);
      }
      if (!on && m) m.remove();
    },
  };
})();
