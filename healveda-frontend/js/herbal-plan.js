let latestSummary = "";

function generateHerbalPlan() {
  const resultDiv = document.getElementById("result");
  const voiceBtn = document.getElementById("voiceBtn");

  resultDiv.classList.remove("hidden");
  voiceBtn.classList.add("hidden");
  resultDiv.innerHTML = "🌱 Generating your herbal plan...";

  const prakriti = document.getElementById("prakriti").value;
  const goal = document.getElementById("goal").value;
  const lifestyle = document.getElementById("lifestyle").value;
  const medicines = document.getElementById("medicines").value;

  fetch("/generate-herbal-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prakriti, goal, lifestyle, medicines })
  })
  .then(res => res.json())
  .then(data => {
    const text = data.response || "";

    // 🔹 Create short summary ourselves
    const sentences = text.split(".").filter(s => s.trim().length > 30);
    latestSummary = sentences.slice(-2).join(". ") + ".";

    resultDiv.innerHTML = `
      <h3 class="text-green-700 text-2xl font-bold mb-4">
        🌿 Your Personalized Herbal Plan
      </h3>

      <div class="space-y-6 text-gray-800 leading-relaxed">

        <div>
          <h4 class="text-green-600 font-semibold mb-2">🌱 Recommended Herbs</h4>
          <ul class="list-disc ml-6">
            ${extractBullets(text, 1, 3)}
          </ul>
        </div>

        <div>
          <h4 class="text-green-600 font-semibold mb-2">🧘 Lifestyle Guidance</h4>
          <ul class="list-disc ml-6">
            ${extractBullets(text, 4, 6)}
          </ul>
        </div>

        <div>
          <h4 class="text-red-600 font-semibold mb-2">⚠️ Safety Note</h4>
          <p>
            ${medicines
              ? "Be mindful while combining herbs with your current medication."
              : "No major safety concerns identified."}
          </p>
        </div>

        <div class="bg-emerald-50 p-4 rounded-lg">
          <h4 class="text-emerald-700 font-semibold mb-1">✨ Short Summary</h4>
          <p>${latestSummary}</p>
        </div>

      </div>
    `;

    voiceBtn.classList.remove("hidden");
  })
  .catch(() => {
    resultDiv.innerHTML = "❌ Unable to generate herbal plan.";
  });
}

// 🔹 Helper: extract numbered items
function extractBullets(text, start, end) {
  const matches = text.match(/\d+\.\s.+/g) || [];
  return matches
    .slice(start - 1, end)
    .map(item => `<li>${item.replace(/\d+\.\s/, "")}</li>`)
    .join("");
}

// 🔊 Voice output
function speakSummary() {
  if (!latestSummary) {
    alert("Summary not ready yet.");
    return;
  }

  const speech = new SpeechSynthesisUtterance(latestSummary);
  speech.lang = "en-IN";
  speech.rate = 0.95;
  speech.pitch = 1;

  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(speech);
}
