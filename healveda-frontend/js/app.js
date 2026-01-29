function sendToBackend() {
  const resultDiv = document.getElementById("result");
  resultDiv.classList.remove("hidden");
  resultDiv.innerHTML = "⏳ Checking wellness risk...";

  const medicines = document.getElementById("medicines").value;
  const herbs = document.getElementById("herbs").value;
  const prakriti = document.getElementById("prakriti").value;

  const symptoms = [];
  document.querySelectorAll(".symptom:checked")
    .forEach(cb => symptoms.push(cb.value));

  fetch("/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      medicines,
      herbs,
      prakriti,
      symptoms
    })
  })
  .then(res => res.json())
  .then(data => {
    console.log("📦 Backend response:", data);

    const text = data.response || "No response generated.";

    resultDiv.innerHTML = `
      <h3 class="text-green-700 font-bold text-lg mb-3">
        🩺 Wellness Safety Check
      </h3>

      <div class="space-y-4 text-gray-800 leading-relaxed">
        ${text
          .replace(/INTRODUCTION:/g, "<h4 class='font-semibold text-green-600'>Introduction</h4>")
          .replace(/INTERACTION_ANALYSIS:/g, "<h4 class='font-semibold text-green-600'>Medication & Herb Interaction</h4>")
          .replace(/AYURVEDIC_PERSPECTIVE:/g, "<h4 class='font-semibold text-green-600'>Ayurvedic Perspective</h4>")
          .replace(/WELLNESS_GUIDANCE:/g, "<h4 class='font-semibold text-green-600'>Wellness Guidance</h4>")
          .replace(/SUMMARY:/g, "<h4 class='font-semibold text-green-600'>Summary Safety Check</h4>")
          .replace(/DISCLAIMER:/g, "<h4 class='font-semibold text-red-600'>Disclaimer</h4>")
          .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
          .replace(/\n/g, "<br>")
        }
      </div>
    `;
  })
  .catch(err => {
    console.error(err);
    resultDiv.innerHTML = "❌ Unable to connect to server.";
  });
}
