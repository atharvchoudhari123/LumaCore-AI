(() => {
  const style = document.createElement("style");
  style.textContent = `
    .media-tools{display:flex;gap:8px;max-width:900px;margin:0 auto 10px}
    .media-tools button{border:1px solid #302d49;background:#15131f;color:#ddd7ff;border-radius:10px;padding:7px 10px;cursor:pointer}
    .media-tools button.active{background:#30265e;border-color:#6651dd;color:white}
    .media-card{margin:12px 0;padding:14px;border:1px solid #292d37;border-radius:14px;background:#101219}
    .media-card img,.media-card video{display:block;max-width:100%;max-height:520px;border-radius:10px;margin-top:10px}
    .media-card a{display:inline-block;margin-top:10px;color:#b9afff}
    .media-status{color:#858da0;font-size:12px;margin-top:8px}
  `;
  document.head.appendChild(style);

  const composer = document.querySelector(".composer");
  const box = document.querySelector(".box");
  const input = document.getElementById("input");
  const send = document.getElementById("send");
  const inner = document.getElementById("inner");

  if (!composer || !box || !input || !send || !inner) return;

  const tools = document.createElement("div");
  tools.className = "media-tools";
  tools.innerHTML = `
    <button type="button" data-media="image">Generate image</button>
    <button type="button" data-media="video">Generate video</button>
  `;
  composer.parentNode.insertBefore(tools, composer);

  let mediaMode = null;
  const buttons = [...tools.querySelectorAll("button")];

  function setMode(mode) {
    mediaMode = mode;
    buttons.forEach(b => b.classList.toggle("active", b.dataset.media === mode));
    if (mode === "image") input.placeholder = "Describe the image you want...";
    else if (mode === "video") input.placeholder = "Describe the video you want...";
    else input.placeholder = "Message LumaCore...";
  }

  buttons.forEach(button => button.addEventListener("click", () => {
    setMode(mediaMode === button.dataset.media ? null : button.dataset.media);
    input.focus();
  }));

  function addMediaCard(kind, data) {
    const card = document.createElement("div");
    card.className = "media-card";
    const title = kind === "image" ? "Generated image" : "Generated video";
    const url = data.url;
    const label = document.createElement("div");
    label.textContent = title;
    card.appendChild(label);

    if (kind === "image") {
      const image = document.createElement("img");
      image.src = url;
      image.alt = data.prompt || title;
      card.appendChild(image);
    } else {
      const video = document.createElement("video");
      video.src = url;
      video.controls = true;
      video.playsInline = true;
      card.appendChild(video);
    }

    const link = document.createElement("a");
    link.href = url;
    link.download = data.filename || (kind === "image" ? "lumacore-image.png" : "lumacore-video.mp4");
    link.textContent = "Download";
    card.appendChild(link);
    inner.appendChild(card);
    requestAnimationFrame(() => {
      const feed = document.getElementById("feed");
      if (feed) feed.scrollTop = feed.scrollHeight;
    });
  }

  function addStatus(text) {
    const row = document.createElement("div");
    row.className = "message";
    row.innerHTML = `<div class="avatar ai">L</div><div class="body"><div class="meta">LumaCore media</div><div class="bubble media-status"></div></div>`;
    row.querySelector(".media-status").textContent = text;
    inner.appendChild(row);
    return row;
  }

  async function generate(kind, prompt) {
    const status = addStatus(kind === "image" ? "Generating image…" : "Generating video…");
    try {
      const endpoint = kind === "image" ? "/v1/media/images" : "/v1/media/videos";
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Media generation failed.");
      status.remove();
      addMediaCard(kind, data);
    } catch (error) {
      status.querySelector(".media-status").textContent = error.message;
    }
  }

  // Replace the existing send button handler with a media-aware wrapper.
  const originalSend = send.onclick;
  send.onclick = () => {
    const prompt = input.value.trim();
    if (mediaMode && prompt) {
      input.value = "";
      const selected = mediaMode;
      setMode(null);
      const userRow = document.createElement("div");
      userRow.className = "message";
      userRow.innerHTML = `<div class="avatar user">You</div><div class="body"><div class="meta">You</div><div class="bubble userBubble"></div></div>`;
      userRow.querySelector(".bubble").textContent = prompt;
      inner.appendChild(userRow);
      generate(selected, prompt);
      return;
    }
    if (typeof originalSend === "function") originalSend();
  };

  input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey && mediaMode) {
      event.preventDefault();
      send.click();
    }
  });
})();
