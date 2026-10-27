document.querySelectorAll("form").forEach((form) => {
  if ((form.method || "get").toLowerCase() === "post" && !form.querySelector("input[name='csrf_token']")) {
    const token = document.querySelector("meta[name='csrf-token']")?.content;
    if (token) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "csrf_token";
      input.value = token;
      form.appendChild(input);
    }
  }
  form.addEventListener("submit", () => {
    const button = form.querySelector("button[type='submit'], button:not([type])");
    if (button) {
      button.disabled = true;
      button.dataset.originalText = button.textContent;
      button.textContent = "Сохраняем…";
    }
  });
});

document.querySelectorAll(".auto-submit-form input[type='file']").forEach((input) => {
  input.addEventListener("change", () => {
    if (input.files && input.files.length > 0) {
      input.form?.requestSubmit();
    }
  });
});
