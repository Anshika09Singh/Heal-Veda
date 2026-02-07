async function scanMedicines() {
  const imageInput = document.getElementById("imageInput");
  const resultDiv = document.getElementById("result");
  const speakBtn = document.getElementById("speakBtn");

  // Hide speaker before scan
  speakBtn.classList.add("hidden");

  if (!imageInput.files.length) {
    alert("Please upload a prescription image");
    return;
  }

  const formData = new FormData();
  formData.append("image", imageInput.files[0]);

  resultDiv.innerHTML = `
    <p class="text-gray-500 font-medium">
      ⏳ Reading prescription using AI & ML...
    </p>
  `;

  try {
    const response = await fetch("/scan-medicines", {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error("Server error");
    }

    const data = await response.json();

    let html = "";

    /* Safety Score */
    html += `
      <div class="bg-white p-4 rounded shadow mb-4">
        <h3 class="font-semibold text-orange-700">📊 Safety Score</h3>
        <p class="text-xl font-bold text-yellow-600">
          ${data.riskScore ?? "N/A"} / 100 (${data.riskLevel ?? "Info"})
        </p>
      </div>
    `;

    /* Medicines */
    html += `
      <div class="bg-white p-4 rounded shadow mb-4">
        <h3 class="font-semibold text-orange-700">💊 Medicines Found</h3>
        ${
          data.medicines && data.medicines.length > 0
            ? `<ul class="list-disc ml-6 text-gray-700">
                ${data.medicines.map(m => `<li>${m}</li>`).join("")}
               </ul>`
            : `<p class="text-gray-500">Medicine names were unclear.</p>`
        }
      </div>
    `;

    /* Timing Advice */
    if (data.timingAdvice && data.timingAdvice.length > 0) {
      html += `
        <div class="bg-white p-4 rounded shadow mb-4">
          <h3 class="font-semibold text-orange-700">⏰ When to Take</h3>
          <ul class="list-disc ml-6 text-gray-700">
            ${data.timingAdvice.map(t =>
              `<li><b>${t.medicine}:</b> ${t.advice}</li>`
            ).join("")}
          </ul>
        </div>
      `;
    }

    /* Alerts */
    if (data.alerts && data.alerts.length > 0) {
      html += `
        <div class="bg-yellow-100 border-l-4 border-yellow-500 p-4 rounded mb-4">
          <h3 class="font-semibold text-yellow-800">⚠️ Safety Alerts</h3>
          <ul class="list-disc ml-6 text-yellow-700">
            ${data.alerts.map(a => `<li>${a}</li>`).join("")}
          </ul>
        </div>
      `;
    }

    /* AI Explanation */
    if (data.aiExplanation) {
      html += `
        <div class="bg-white p-4 rounded shadow">
          <h3 class="font-semibold text-orange-700">
            🧠 Simple Explanation (AI)
          </h3>
          <p class="text-gray-700 whitespace-pre-line">
            ${data.aiExplanation}
          </p>
        </div>
      `;
    }

    resultDiv.innerHTML = html;

    // ✅ Show speaker button after successful result
    speakBtn.classList.remove("hidden");

  } catch (err) {
    console.error(err);
    resultDiv.innerHTML = `
      <p class="text-red-600 font-semibold">
        ❌ Failed to scan prescription
      </p>
    `;
  }
}

/* 🔊 SPEAK RESULT */
function speakResult() {
  const resultText = document.getElementById("result").innerText;

  if (!resultText.trim()) {
    alert("Nothing to read yet");
    return;
  }

  const utterance = new SpeechSynthesisUtterance(resultText);
  utterance.lang = "en-IN";   // Indian English
  utterance.rate = 0.9;       // Slower, clear
  utterance.pitch = 1;

  window.speechSynthesis.cancel(); // stop previous
  window.speechSynthesis.speak(utterance);
}
