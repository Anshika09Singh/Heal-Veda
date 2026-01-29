function generateHerbalPlan() {
  const resultDiv = document.getElementById("result");
  resultDiv.classList.remove("hidden");
  resultDiv.innerHTML = "🌱 Generating your herbal plan...";

  const prakriti = document.getElementById("prakriti").value;
  const goal = document.getElementById("goal").value;
  const lifestyle = document.getElementById("lifestyle").value;
  const medicines = document.getElementById("medicines").value;

  fetch("/generate-herbal-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prakriti,
      goal,
      lifestyle,
      medicines
    })
  })
  .then(res => res.json())
  .then(data => {
    const text = data.response || "No plan generated.";

    resultDiv.innerHTML = `
      <h3 class="text-green-700 text-xl font-bold mb-4">
        🌿 Your Personalized Herbal Plan
      </h3>

      <div class="space-y-4 leading-relaxed text-gray-800">
        ${text
          .replace(/HERBAL_PLAN:/g, "<h4 class='font-semibold text-green-600'>Herbal Plan</h4>")
          .replace(/WHY_IT_WORKS:/g, "<h4 class='font-semibold text-green-600'>Why It Works</h4>")
          .replace(/HOW_TO_USE:/g, "<h4 class='font-semibold text-green-600'>How To Use</h4>")
          .replace(/LIFESTYLE_TIPS:/g, "<h4 class='font-semibold text-green-600'>Lifestyle Tips</h4>")
          .replace(/SAFETY_NOTES:/g, "<h4 class='font-semibold text-red-600'>Safety Notes</h4>")
          .replace(/DISCLAIMER:/g, "<h4 class='font-semibold text-gray-500'>Disclaimer</h4>")
          .replace(/\n/g, "<br>")
        }
      </div>
    `;
  })
  .catch(() => {
    resultDiv.innerHTML = "❌ Unable to generate herbal plan.";
  });
}
