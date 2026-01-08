const output = document.getElementById("output");
const forms = document.querySelectorAll(".api-form");

const apiPrefix = "/api";

function writeOutput(data) {
  if (!output) {
    return;
  }
  output.textContent = JSON.stringify(data, null, 2);
}

function parseValue(input) {
  if (input.dataset.json !== undefined) {
    const raw = input.value.trim();
    if (!raw) {
      const fallback = input.dataset.default || "{}";
      return JSON.parse(fallback);
    }
    return JSON.parse(raw);
  }

  if (input.type === "checkbox") {
    return input.checked;
  }

  if (input.dataset.number !== undefined) {
    const num = Number(input.value);
    if (Number.isNaN(num)) {
      return null;
    }
    return num;
  }

  return input.value;
}

function buildPayload(form) {
  const payload = {};
  const inputs = form.querySelectorAll("input, select, textarea");

  inputs.forEach((input) => {
    const name = input.name;
    if (!name) {
      return;
    }

    const value = parseValue(input);
    if (value === "" || value === null) {
      return;
    }

    payload[name] = value;
  });

  return payload;
}

async function handleSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const endpoint = form.dataset.endpoint;
  if (!endpoint) {
    return;
  }

  let payload;
  try {
    payload = buildPayload(form);
  } catch (err) {
    writeOutput({ error: "Invalid JSON", detail: err.message });
    return;
  }

  try {
    const response = await fetch(`${apiPrefix}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      writeOutput({ error: response.status, detail: data });
      return;
    }

    writeOutput(data);
  } catch (err) {
    writeOutput({ error: "Network error", detail: err.message });
  }
}

forms.forEach((form) => {
  form.addEventListener("submit", handleSubmit);
});

writeOutput({ status: "Ready for input" });
