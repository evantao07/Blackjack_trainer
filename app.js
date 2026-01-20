// app.js
const $ = (id) => document.getElementById(id);

function renderCards(containerId, cards, hideSecond = false) {
  const wrap = $(containerId);
  wrap.innerHTML = "";

  cards.forEach((c, i) => {
    const div = document.createElement("div");
    div.className = "card" + (hideSecond && i === 1 ? " back" : "");

    const rank = document.createElement("div");
    rank.className = "rank";
    const suit = document.createElement("div");
    suit.className = "suit";

    if (hideSecond && i === 1) {
      rank.textContent = "";
      suit.textContent = "";
    } else {
      rank.textContent = c.slice(0, -1);
      suit.textContent = c.slice(-1);
    }

    div.appendChild(rank);
    div.appendChild(suit);
    wrap.appendChild(div);
  });
}

function setAcc(sAcc, aAcc) {
  const sPct = sAcc.total ? ((sAcc.correct / sAcc.total) * 100).toFixed(1) : "0.0";
  const aPct = aAcc.total ? ((aAcc.correct / aAcc.total) * 100).toFixed(1) : "0.0";
  $("sessionAcc").textContent = `${sAcc.correct}/${sAcc.total} (${sPct}%)`;
  $("allTimeAcc").textContent = `${aAcc.correct}/${aAcc.total} (${aPct}%)`;
}

function applyState(data) {
  renderCards("dealerCards", data.dealer, data.hideDealerSecond);
  renderCards("playerCards", data.player, false);

  // Player total always shows normally
  $("playerTotal").textContent = data.playerTotal ?? "—";

  // Dealer "Total" shows upcard during player turn, then true total when revealed
  $("dealerTotal").textContent = data.hideDealerSecond
    ? (data.dealerUpcard ?? "—")   // show upcard like "A" or "10"
    : (data.dealerTotal ?? "—");  // show actual dealer total number

  setAcc(data.sessionAccuracy, data.allTimeAccuracy);

  $("btnHit").disabled = data.roundOver;
  $("btnStand").disabled = data.roundOver;

  // Show New Round only when round is over
  $("btnNew").classList.toggle("hidden", !data.roundOver);
}



async function apiGet(path) {
  const res = await fetch(path);
  return await res.json();
}

async function apiPost(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return await res.json();
}

$("btnNew").addEventListener("click", async () => {
  const data = await apiPost("/api/new-round");
  applyState(data);
});

$("btnHit").addEventListener("click", async () => {
  const data = await apiPost("/api/action", { action: "H" });
  applyState(data);
});

$("btnStand").addEventListener("click", async () => {
  const data = await apiPost("/api/action", { action: "S" });
  applyState(data);
});

// start game on load
(async () => {
  const data = await apiGet("/api/start");
  applyState(data);
})();
