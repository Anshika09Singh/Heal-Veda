async function scanMedicines() {
  const manualMedicines = document.getElementById("manualMedicines").value;
  const prescriptionText = document.getElementById("prescriptionText").value;
  const imageInput = document.querySelector('input[type="file"]');

  const formData = new FormData();
  formData.append("manualMedicines", manualMedicines);
  formData.append("prescriptionText", prescriptionText);

  if (imageInput.files.length > 0) {
    formData.append("image", imageInput.files[0]);
  }

  const res = await fetch("/scan-medicines", {
    method: "POST",
    body: formData
  });

  const data = await res.json();

  if (data.error) {
    alert(data.error);
    return;
  }

  // Update UI
  document.querySelector(".text-xl.font-bold.text-yellow-600").innerText =
    `${data.riskScore} / 100 (${data.riskLevel})`;

  document.querySelector("ul").innerHTML =
    data.timingAdvice.map(
      t => `<li>${t.medicine}: ${t.advice}</li>`
    ).join("");

  document.querySelector(".text-yellow-700").innerText =
    data.alerts.join(", ");

  document.querySelector(".text-gray-700").innerText =
    data.aiExplanation;
}
