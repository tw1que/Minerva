const apiPrefix = "/api";

const medicalTraceability = document.body?.dataset.medicalTraceability === "true";

const state = {
  token: localStorage.getItem("minerva_token"),
  user: null,
  pages: {
    catalog: 1,
    inventory: 1,
    movements: 1,
    orders: 1,
  },
  templates: new Map(),
  inventoryItems: new Map(),
  activeOrderId: null,
  activeInventoryId: null,
};

const tabs = document.querySelectorAll(".tab");
const views = document.querySelectorAll(".view");

const userLabel = document.getElementById("user-label");
const logoutButton = document.getElementById("logout-button");
const loginModal = document.getElementById("login-modal");
const loginForm = document.getElementById("login-form");
const loginUsername = document.getElementById("login-username");
const loginPassword = document.getElementById("login-password");
const loginStatus = document.getElementById("login-status");
const toast = document.getElementById("toast");

const catalogSearch = document.getElementById("catalog-search");
const catalogManufacturer = document.getElementById("catalog-manufacturer");
const catalogAttrKey = document.getElementById("catalog-attr-key");
const catalogAttrVal = document.getElementById("catalog-attr-val");
const catalogFilter = document.getElementById("catalog-filter");
const catalogTableBody = document.querySelector("#catalog-table tbody");

const templateForm = document.getElementById("template-form");
const addTemplateSpec = document.getElementById("add-template-spec");
const templateSpecsContainer = document.getElementById("template-specs");
const templateSpecsJson = document.getElementById("template-specs-json");
const templateSkuJson = document.getElementById("template-sku-json");

const itemForm = document.getElementById("item-form");
const itemTemplateSelect = document.getElementById("item-template-select");
const itemAttributesContainer = document.getElementById("item-attributes");
const itemAttributesJson = document.getElementById("item-attributes-json");
const medicalTraceabilityTag = document.getElementById("medical-traceability-tag");
const medicalItemNote = document.getElementById("medical-item-note");

const inventorySearch = document.getElementById("inventory-search");
const inventoryManufacturer = document.getElementById("inventory-manufacturer");
const inventoryAttrKey = document.getElementById("inventory-attr-key");
const inventoryAttrVal = document.getElementById("inventory-attr-val");
const inventoryFilter = document.getElementById("inventory-filter");
const inventoryTableBody = document.querySelector("#inventory-table tbody");
const inventoryDetailTitle = document.getElementById("inventory-detail-title");
const inventoryLotsBody = document.querySelector("#inventory-lots-table tbody");
const inventoryMovementsBody = document.querySelector("#inventory-movements-table tbody");

const movementForm = document.getElementById("movement-form");
const movementItemSearch = document.getElementById("movement-item-search");
const movementItemOptions = document.getElementById("movement-item-options");
const movementItemMeta = document.getElementById("movement-item-meta");
const movementType = document.getElementById("movement-type");
const movementReason = document.getElementById("movement-reason");
const movementQty = document.getElementById("movement-qty");
const movementUom = document.getElementById("movement-uom");
const movementLot = document.getElementById("movement-lot");
const lotToggle = document.getElementById("lot-toggle");
const lotCreate = document.getElementById("lot-create");
const lotCode = document.getElementById("lot-code");
const lotSupplier = document.getElementById("lot-supplier");
const lotMfg = document.getElementById("lot-mfg");
const lotExp = document.getElementById("lot-exp");
const movementComment = document.getElementById("movement-comment");
const movementSearch = document.getElementById("movement-search");
const movementFilterReason = document.getElementById("movement-filter-reason");
const movementFilter = document.getElementById("movement-filter");
const movementsTableBody = document.querySelector("#movements-table tbody");
const medicalMovementNote = document.getElementById("medical-movement-note");

const orderForm = document.getElementById("order-form");
const orderNumber = document.getElementById("order-number");
const orderNotes = document.getElementById("order-notes");
const orderSearch = document.getElementById("order-search");
const orderStatusFilter = document.getElementById("order-status-filter");
const orderFilter = document.getElementById("order-filter");
const ordersTableBody = document.querySelector("#orders-table tbody");
const orderDetailTitle = document.getElementById("order-detail-title");
const orderLineForm = document.getElementById("order-line-form");
const orderItemSearch = document.getElementById("order-item-search");
const orderItemOptions = document.getElementById("order-item-options");
const orderItemQty = document.getElementById("order-item-qty");
const orderLinesBody = document.querySelector("#order-lines-table tbody");

const movementReasonOptions = {
  inbound: ["RECEIPT", "RETURN", "TRANSFER"],
  outbound: ["CONSUME", "SCRAP", "TRANSFER"],
  adjustment: ["ADJUST"],
};

function showToast(message) {
  if (!toast) {
    return;
  }
  toast.textContent = message;
  toast.classList.add("is-visible");
  clearTimeout(showToast.timeout);
  showToast.timeout = setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 2400);
}

function setStatus(element, message, tone) {
  if (!element) {
    return;
  }
  element.textContent = message || "";
  element.classList.remove("form-status--success", "form-status--error");
  if (tone === "success") {
    element.classList.add("form-status--success");
  }
  if (tone === "error") {
    element.classList.add("form-status--error");
  }
}

function clearStatus(element) {
  setStatus(element, "", null);
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return escapeHtml(value);
  }
  return date.toLocaleString();
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return escapeHtml(value);
  }
  return date.toLocaleDateString();
}

function formatQty(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  const num = Number(value);
  if (Number.isNaN(num)) {
    return escapeHtml(value);
  }
  return num.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}

function formatAttributes(attributes) {
  if (!attributes || Object.keys(attributes).length === 0) {
    return "-";
  }
  return Object.entries(attributes)
    .map(([key, value]) => `${key}: ${value}`)
    .join(", ");
}

function buildQuery(params) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") {
      return;
    }
    searchParams.append(key, value);
  });
  return searchParams.toString();
}

function debounce(fn, delay = 250) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), delay);
  };
}

async function parseError(response) {
  try {
    const data = await response.json();
    if (data && data.detail) {
      return data.detail;
    }
  } catch (error) {
    return `${response.status} ${response.statusText}`.trim();
  }
  return `${response.status} ${response.statusText}`.trim();
}

async function apiRequest(path, options = {}) {
  const { method = "GET", body = null, isForm = false } = options;
  const headers = {
    Accept: "application/json",
  };

  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  let payload = body;
  if (body !== null) {
    if (isForm) {
      headers["Content-Type"] = "application/x-www-form-urlencoded";
    } else {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }
  }

  const response = await fetch(`${apiPrefix}${path}`, {
    method,
    headers,
    body: payload,
  });

  if (!response.ok) {
    const message = await parseError(response);
    if (response.status === 401) {
      clearSession("Please sign in to continue.");
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function openLoginModal(message) {
  if (!loginModal) {
    return;
  }
  loginModal.classList.add("is-visible");
  loginModal.setAttribute("aria-hidden", "false");
  if (message) {
    setStatus(loginStatus, message, "error");
  }
}

function closeLoginModal() {
  if (!loginModal) {
    return;
  }
  loginModal.classList.remove("is-visible");
  loginModal.setAttribute("aria-hidden", "true");
  clearStatus(loginStatus);
}

function applyRole() {
  const canWrite = Boolean(state.user && state.user.role !== "VIEWER");
  document.querySelectorAll("[data-requires='write']").forEach((section) => {
    section.querySelectorAll("input, select, textarea, button").forEach((control) => {
      control.disabled = !canWrite;
    });
  });
}

function updateUserUI() {
  if (state.user) {
    userLabel.textContent = `${state.user.username} (${state.user.role})`;
    logoutButton.disabled = false;
  } else {
    userLabel.textContent = "Not signed in";
    logoutButton.disabled = true;
  }
  applyRole();
}

function applyMedicalTraceabilityUI() {
  if (!medicalTraceability) {
    return;
  }

  medicalTraceabilityTag?.classList.remove("is-hidden");
  medicalItemNote?.classList.remove("is-hidden");
  medicalMovementNote?.classList.remove("is-hidden");

  const trackLotsInput = itemForm.querySelector("[name='track_lots']");
  if (trackLotsInput) {
    trackLotsInput.checked = true;
    trackLotsInput.disabled = true;
  }

  movementQty.value = "1";
  movementQty.step = "1";
  movementQty.min = "1";
  movementQty.max = "1";
  movementQty.readOnly = true;
}

function clearSession(message) {
  state.token = null;
  state.user = null;
  localStorage.removeItem("minerva_token");
  updateUserUI();
  openLoginModal(message || "Sign in to continue.");
}

async function loadSession() {
  if (!state.token) {
    updateUserUI();
    openLoginModal("Sign in to manage inventory.");
    return;
  }
  try {
    const user = await apiRequest("/auth/me");
    state.user = user;
    updateUserUI();
    closeLoginModal();
  } catch (error) {
    clearSession("Session expired. Please sign in.");
  }
}

function setView(name) {
  views.forEach((view) => {
    view.classList.toggle("is-active", view.id === `view-${name}`);
  });
  tabs.forEach((tab) => {
    tab.classList.toggle("is-active", tab.dataset.view === name);
  });
}

function updatePager(key, page, pageSize, total) {
  const pager = document.querySelector(`[data-pager="${key}"]`);
  if (!pager) {
    return;
  }
  const pageInfo = pager.querySelector("[data-page='info']");
  const prev = pager.querySelector("[data-page='prev']");
  const next = pager.querySelector("[data-page='next']");
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  pageInfo.textContent = `Page ${page} of ${totalPages}`;
  prev.disabled = page <= 1;
  next.disabled = page >= totalPages;
}

function setupPagers() {
  const loaders = {
    catalog: loadCatalog,
    inventory: loadInventory,
    movements: loadMovements,
    orders: loadOrders,
  };
  document.querySelectorAll("[data-pager]").forEach((pager) => {
    const key = pager.dataset.pager;
    const prev = pager.querySelector("[data-page='prev']");
    const next = pager.querySelector("[data-page='next']");
    if (prev) {
      prev.addEventListener("click", () => {
        if (state.pages[key] > 1) {
          state.pages[key] -= 1;
          loaders[key]();
        }
      });
    }
    if (next) {
      next.addEventListener("click", () => {
        state.pages[key] += 1;
        loaders[key]();
      });
    }
  });
}

function parseCommaList(value) {
  if (!value) {
    return [];
  }
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseKeyValueMap(value) {
  if (!value) {
    return null;
  }
  const map = {};
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .forEach((pair) => {
      const parts = pair.split("=");
      if (parts.length < 2) {
        return;
      }
      const key = parts.shift().trim();
      const mapped = parts.join("=").trim();
      if (!key || !mapped) {
        return;
      }
      map[key] = mapped;
    });
  return Object.keys(map).length ? map : null;
}

function parseMaybeNumber(value) {
  if (value === null || value === undefined) {
    return null;
  }
  const text = String(value).trim();
  if (!text) {
    return null;
  }
  const num = Number(text);
  if (Number.isNaN(num)) {
    return text;
  }
  return num;
}

function parseAllowedValue(value, type) {
  const text = String(value).trim();
  if (!text) {
    return null;
  }
  if (type === "int") {
    const num = Number(text);
    if (!Number.isInteger(num)) {
      throw new Error(`Allowed value '${text}' must be an integer.`);
    }
    return num;
  }
  if (type === "decimal") {
    const num = Number(text);
    if (Number.isNaN(num)) {
      throw new Error(`Allowed value '${text}' must be numeric.`);
    }
    return num;
  }
  if (type === "bool") {
    const normalized = text.toLowerCase();
    if (["true", "1", "yes", "y"].includes(normalized)) {
      return true;
    }
    if (["false", "0", "no", "n"].includes(normalized)) {
      return false;
    }
    throw new Error(`Allowed value '${text}' must be boolean.`);
  }
  return text;
}

function addTemplateSpecRow() {
  const row = document.createElement("div");
  row.className = "field-row";
  row.innerHTML = `
    <label>
      Key
      <input type="text" class="spec-key" placeholder="diameter" required />
    </label>
    <label>
      Type
      <select class="spec-type">
        <option value="string">string</option>
        <option value="int">int</option>
        <option value="decimal">decimal</option>
        <option value="enum">enum</option>
        <option value="bool">bool</option>
      </select>
    </label>
    <label class="checkbox">
      <input type="checkbox" class="spec-required" />
      Required
    </label>
    <label class="checkbox">
      <input type="checkbox" class="spec-identity" checked />
      Identity
    </label>
    <label class="checkbox">
      <input type="checkbox" class="spec-sku" checked />
      In SKU
    </label>
    <label>
      Allowed Values
      <input type="text" class="spec-values" placeholder="A1,A2" />
    </label>
    <label>
      Range Min
      <input type="number" class="spec-min" step="0.001" />
    </label>
    <label>
      Range Max
      <input type="number" class="spec-max" step="0.001" />
    </label>
    <label>
      Range Step
      <input type="number" class="spec-step" step="0.001" />
    </label>
    <label>
      Unit
      <input type="text" class="spec-unit" placeholder="mm" />
    </label>
    <label>
      Normalize Flags
      <input type="text" class="spec-normalize" placeholder="lower,strip" />
    </label>
    <label>
      Enum Map
      <input type="text" class="spec-enum-map" placeholder="multi=multilayer" />
    </label>
    <label>
      SKU Map
      <input type="text" class="spec-sku-map" placeholder="multilayer=ML" />
    </label>
    <label>
      SKU Pad Width
      <input type="number" class="spec-pad" min="1" placeholder="2" />
    </label>
    <label>
      Pad Char
      <input type="text" class="spec-pad-char" maxlength="1" placeholder="0" />
    </label>
    <div class="field-actions">
      <button type="button" class="ghost field-remove">Remove</button>
    </div>
  `;
  row.querySelector(".field-remove").addEventListener("click", () => {
    row.remove();
  });
  templateSpecsContainer.appendChild(row);
}

function collectTemplateSpecs() {
  const rows = templateSpecsContainer.querySelectorAll(".field-row");
  const specs = [];
  rows.forEach((row) => {
    const key = row.querySelector(".spec-key").value.trim();
    const type = row.querySelector(".spec-type").value;
    if (!key) {
      throw new Error("Attribute spec key is required.");
    }

    const required = row.querySelector(".spec-required").checked;
    const includeInIdentity = row.querySelector(".spec-identity").checked;
    const includeInSku = row.querySelector(".spec-sku").checked;

    const valuesText = row.querySelector(".spec-values").value.trim();
    const allowedValuesRaw = parseCommaList(valuesText);
    const allowedValues = allowedValuesRaw.length
      ? allowedValuesRaw
          .map((value) => parseAllowedValue(value, type))
          .filter((value) => value !== null)
      : null;

    const rangeMin = parseMaybeNumber(row.querySelector(".spec-min").value);
    const rangeMax = parseMaybeNumber(row.querySelector(".spec-max").value);
    const rangeStep = parseMaybeNumber(row.querySelector(".spec-step").value);
    const hasRange = rangeMin !== null || rangeMax !== null || rangeStep !== null;
    if (allowedValues && hasRange) {
      throw new Error(`Spec '${key}' cannot have both allowed values and a range.`);
    }
    if (hasRange && !["int", "decimal"].includes(type)) {
      throw new Error(`Spec '${key}' can only use ranges for int or decimal types.`);
    }

    let allowedRange = null;
    if (hasRange) {
      allowedRange = {};
      if (rangeMin !== null) {
        allowedRange.min = rangeMin;
      }
      if (rangeMax !== null) {
        allowedRange.max = rangeMax;
      }
      if (rangeStep !== null) {
        allowedRange.step = rangeStep;
      }
    }

    if (type === "enum" && !allowedValues) {
      throw new Error(`Enum spec '${key}' requires allowed values.`);
    }

    const unit = row.querySelector(".spec-unit").value.trim() || null;

    const normalizeFlags = parseCommaList(row.querySelector(".spec-normalize").value);
    const enumMap = parseKeyValueMap(row.querySelector(".spec-enum-map").value);
    let normalize = null;
    if (enumMap || normalizeFlags.length) {
      if (enumMap) {
        normalize = {};
        normalizeFlags.forEach((flag) => {
          normalize[flag] = true;
        });
        normalize.enum_map = enumMap;
      } else {
        normalize = normalizeFlags;
      }
    }

    const skuMap = parseKeyValueMap(row.querySelector(".spec-sku-map").value);
    const padWidthRaw = row.querySelector(".spec-pad").value.trim();
    const padChar = row.querySelector(".spec-pad-char").value.trim();
    let skuPad = null;
    if (padWidthRaw) {
      const padWidth = Number(padWidthRaw);
      if (!Number.isInteger(padWidth) || padWidth <= 0) {
        throw new Error(`SKU pad width must be a positive integer for '${key}'.`);
      }
      if (padChar) {
        if (padChar.length !== 1) {
          throw new Error(`Pad char must be a single character for '${key}'.`);
        }
        skuPad = { width: padWidth, char: padChar };
      } else {
        skuPad = padWidth;
      }
    } else if (padChar) {
      throw new Error(`Pad width is required when pad char is set for '${key}'.`);
    }

    specs.push({
      key,
      type,
      required,
      allowed_values: allowedValues,
      allowed_range: allowedRange,
      unit,
      normalize,
      sku_pad: skuPad,
      sku_map: skuMap,
      include_in_identity: includeInIdentity,
      include_in_sku: includeInSku,
    });
  });

  if (!specs.length) {
    throw new Error("Add at least one attribute spec.");
  }

  return specs;
}

function collectSkuRule() {
  const prefix = templateForm.querySelector("[name='sku_prefix']").value.trim();
  const separatorRaw = templateForm.querySelector("[name='sku_separator']").value.trim();
  const tokensRaw = templateForm.querySelector("[name='sku_tokens']").value.trim();
  const versionRaw = templateForm.querySelector("[name='sku_version']").value.trim();
  const freezeExisting = templateForm.querySelector(
    "[name='freeze_existing_skus']"
  ).checked;

  if (!prefix) {
    throw new Error("SKU prefix is required.");
  }
  const separator = separatorRaw || "-";
  const tokens = parseCommaList(tokensRaw);
  if (!tokens.length) {
    throw new Error("SKU tokens are required.");
  }
  const uniqueTokens = new Set(tokens);
  if (uniqueTokens.size !== tokens.length) {
    throw new Error("SKU tokens must be unique.");
  }

  let version = 1;
  if (versionRaw) {
    version = Number(versionRaw);
    if (!Number.isInteger(version) || version <= 0) {
      throw new Error("SKU rule version must be a positive integer.");
    }
  }

  return {
    prefix,
    separator,
    tokens,
    version,
    freeze_existing_skus: freezeExisting,
  };
}

function renderAttributeFields(specs) {
  itemAttributesContainer.innerHTML = "";
  if (!specs || specs.length === 0) {
    itemAttributesContainer.innerHTML = "<p class='muted'>No attribute specs defined.</p>";
    return;
  }

  specs.forEach((spec) => {
    const type = String(spec.type || "string").toLowerCase();
    const label = document.createElement("label");
    const title = document.createElement("span");
    title.textContent = `${spec.key} (${type})`;
    label.appendChild(title);

    if (spec.allowed_values && spec.allowed_values.length) {
      const hint = document.createElement("span");
      hint.className = "hint";
      hint.textContent = `Allowed: ${spec.allowed_values.join(", ")}`;
      label.appendChild(hint);
    }

    let input;
    if (type === "enum" && spec.allowed_values && spec.allowed_values.length) {
      input = document.createElement("select");
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "Select";
      input.appendChild(blank);
      spec.allowed_values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        input.appendChild(option);
      });
    } else if (type === "bool") {
      input = document.createElement("select");
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "Select";
      input.appendChild(blank);
      ["true", "false"].forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        input.appendChild(option);
      });
    } else {
      input = document.createElement("input");
      if (type === "int" || type === "decimal") {
        input.type = "number";
        input.step = type === "int" ? "1" : "0.001";
        if (spec.allowed_range) {
          if (spec.allowed_range.min !== undefined && spec.allowed_range.min !== null) {
            input.min = spec.allowed_range.min;
          }
          if (spec.allowed_range.max !== undefined && spec.allowed_range.max !== null) {
            input.max = spec.allowed_range.max;
          }
          if (spec.allowed_range.step !== undefined && spec.allowed_range.step !== null) {
            input.step = spec.allowed_range.step;
          }
        }
      } else {
        input.type = "text";
      }
      if (spec.unit) {
        input.placeholder = spec.unit;
      }
    }

    input.dataset.fieldKey = spec.key;
    input.dataset.fieldType = type;
    input.dataset.required = spec.required ? "true" : "false";

    if (spec.required) {
      input.required = true;
    }

    label.appendChild(input);
    itemAttributesContainer.appendChild(label);
  });
}

function collectAttributes() {
  const attributes = {};
  const inputs = itemAttributesContainer.querySelectorAll("[data-field-key]");
  inputs.forEach((input) => {
    const key = input.dataset.fieldKey;
    const type = input.dataset.fieldType;
    const required = input.dataset.required === "true";
    const valueRaw = input.value.trim();

    if (!valueRaw) {
      if (required) {
        throw new Error(`${key} is required.`);
      }
      return;
    }

    if (type === "int") {
      const parsed = Number(valueRaw);
      if (!Number.isInteger(parsed)) {
        throw new Error(`${key} must be an integer.`);
      }
      attributes[key] = parsed;
      return;
    }

    if (type === "decimal") {
      const parsed = Number(valueRaw);
      if (Number.isNaN(parsed)) {
        throw new Error(`${key} must be a number.`);
      }
      attributes[key] = valueRaw;
      return;
    }

    if (type === "bool") {
      const normalized = valueRaw.toLowerCase();
      if (["true", "1", "yes", "y"].includes(normalized)) {
        attributes[key] = true;
        return;
      }
      if (["false", "0", "no", "n"].includes(normalized)) {
        attributes[key] = false;
        return;
      }
      throw new Error(`${key} must be true or false.`);
    }

    attributes[key] = valueRaw;
  });

  return attributes;
}

function populateManufacturerSelects(manufacturers) {
  document.querySelectorAll("[data-manufacturer-select]").forEach((select) => {
    const placeholder = select.dataset.placeholder || "All";
    const currentValue = select.value;
    select.innerHTML = "";
    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = placeholder;
    select.appendChild(placeholderOption);
    manufacturers.forEach((manufacturer) => {
      const option = document.createElement("option");
      option.value = manufacturer.id;
      option.textContent = manufacturer.name;
      select.appendChild(option);
    });
    if (currentValue) {
      select.value = currentValue;
    }
  });
}

function populateTemplateSelect(templates) {
  const currentValue = itemTemplateSelect.value;
  itemTemplateSelect.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select template";
  itemTemplateSelect.appendChild(placeholder);
  templates.forEach((template) => {
    const option = document.createElement("option");
    option.value = template.id;
    option.textContent = template.name;
    itemTemplateSelect.appendChild(option);
  });
  if (currentValue) {
    itemTemplateSelect.value = currentValue;
  }
}

async function fetchTemplate(templateId) {
  const id = Number(templateId);
  const cached = state.templates.get(id);
  if (cached && cached.attribute_specs) {
    return cached;
  }
  const template = await apiRequest(`/templates/${id}`);
  state.templates.set(template.id, template);
  return template;
}

function formatItemOption(item) {
  return `${item.product_code} - ${item.template_name}`;
}

function findItemMatch(value, items) {
  const normalized = value.trim().toLowerCase();
  return items.find((item) => {
    return (
      formatItemOption(item).toLowerCase() === normalized ||
      item.product_code.toLowerCase() === normalized
    );
  });
}

function bindItemSearch(input, list, onSelect) {
  let results = [];

  const loadOptions = async (term) => {
    if (!term || term.length < 2) {
      list.innerHTML = "";
      results = [];
      return;
    }

    const query = buildQuery({
      search: term,
      page: 1,
      page_size: 20,
    });
    const data = await apiRequest(`/catalog/items?${query}`);
    results = data.items || [];
    list.innerHTML = results
      .map((item) => `<option value="${escapeHtml(formatItemOption(item))}"></option>`)
      .join("");
  };

  const debouncedLoad = debounce(loadOptions, 300);

  input.addEventListener("input", () => {
    input.dataset.itemId = "";
    if (onSelect) {
      onSelect(null);
    }
    debouncedLoad(input.value.trim());
  });

  input.addEventListener("change", () => {
    const match = findItemMatch(input.value, results);
    if (match) {
      input.dataset.itemId = match.id;
      input.value = formatItemOption(match);
      if (onSelect) {
        Promise.resolve(onSelect(match));
      }
    } else {
      input.dataset.itemId = "";
      if (onSelect) {
        onSelect(null);
      }
    }
  });
}

async function loadManufacturers() {
  const query = buildQuery({ page: 1, page_size: 200 });
  const data = await apiRequest(`/manufacturers?${query}`);
  populateManufacturerSelects(data.items || []);
}

async function loadTemplates() {
  const query = buildQuery({ page: 1, page_size: 200 });
  const data = await apiRequest(`/templates?${query}`);
  state.templates = new Map();
  (data.items || []).forEach((template) => {
    state.templates.set(template.id, template);
  });
  populateTemplateSelect(data.items || []);
}

async function loadCatalog(page = state.pages.catalog) {
  const query = buildQuery({
    search: catalogSearch.value.trim(),
    manufacturer_id: catalogManufacturer.value,
    attr_key: catalogAttrKey.value.trim(),
    attr_val: catalogAttrVal.value.trim(),
    page,
    page_size: 25,
  });
  const data = await apiRequest(`/catalog/items?${query}`);
  const items = data.items || [];
  state.pages.catalog = data.page;
  if (items.length === 0) {
    catalogTableBody.innerHTML = "<tr><td colspan='5'>No items found.</td></tr>";
  } else {
    catalogTableBody.innerHTML = items
      .map((item) => {
        return `
          <tr>
            <td>${escapeHtml(item.product_code)}</td>
            <td>${escapeHtml(item.template_name)}</td>
            <td>${escapeHtml(item.manufacturer_name || "-")}</td>
            <td>${escapeHtml(formatAttributes(item.attributes))}</td>
            <td>${escapeHtml(item.uom)}</td>
          </tr>
        `;
      })
      .join("");
  }
  updatePager("catalog", data.page, data.page_size, data.total);
}

async function loadInventory(page = state.pages.inventory) {
  const query = buildQuery({
    search: inventorySearch.value.trim(),
    manufacturer_id: inventoryManufacturer.value,
    attr_key: inventoryAttrKey.value.trim(),
    attr_val: inventoryAttrVal.value.trim(),
    page,
    page_size: 25,
  });
  const data = await apiRequest(`/inventory/summary?${query}`);
  const items = data.items || [];
  state.pages.inventory = data.page;
  state.inventoryItems = new Map();
  items.forEach((item) => {
    state.inventoryItems.set(item.item_id, item);
  });

  if (items.length === 0) {
    inventoryTableBody.innerHTML = "<tr><td colspan='8'>No inventory records.</td></tr>";
  } else {
    inventoryTableBody.innerHTML = items
      .map((item) => {
        return `
          <tr>
            <td>${escapeHtml(item.product_code)}</td>
            <td>${escapeHtml(item.template_name)}</td>
            <td>${escapeHtml(item.manufacturer_name || "-")}</td>
            <td>${formatQty(item.on_hand)}</td>
            <td>${formatQty(item.reserved)}</td>
            <td>${formatQty(item.available)}</td>
            <td>${formatDateTime(item.last_movement)}</td>
            <td><button type="button" class="ghost" data-inventory-id="${item.item_id}">View</button></td>
          </tr>
        `;
      })
      .join("");
  }

  inventoryTableBody.querySelectorAll("[data-inventory-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const itemId = Number(button.dataset.inventoryId);
      loadInventoryDetail(itemId);
    });
  });

  updatePager("inventory", data.page, data.page_size, data.total);
}

async function loadInventoryDetail(itemId) {
  state.activeInventoryId = itemId;
  const item = state.inventoryItems.get(itemId);
  if (item) {
    inventoryDetailTitle.textContent = `${item.product_code} - ${item.template_name}`;
  } else {
    inventoryDetailTitle.textContent = `Item ${itemId}`;
  }

  const lotsQuery = buildQuery({ item_id: itemId, page: 1, page_size: 50 });
  const lotsData = await apiRequest(`/lots?${lotsQuery}`);
  const lots = lotsData.items || [];

  if (lots.length === 0) {
    inventoryLotsBody.innerHTML = "<tr><td colspan='5'>No lots.</td></tr>";
  } else {
    inventoryLotsBody.innerHTML = lots
      .map((lot) => {
        return `
          <tr>
            <td>${escapeHtml(lot.instance_sku)}</td>
            <td>${escapeHtml(lot.lot_code)}</td>
            <td>${escapeHtml(lot.supplier_name || "-")}</td>
            <td>${formatDate(lot.received_at)}</td>
            <td>${formatDate(lot.expires_at)}</td>
          </tr>
        `;
      })
      .join("");
  }

  const movesQuery = buildQuery({ item_id: itemId, page: 1, page_size: 20 });
  const movesData = await apiRequest(`/movements?${movesQuery}`);
  const moves = movesData.items || [];

  if (moves.length === 0) {
    inventoryMovementsBody.innerHTML = "<tr><td colspan='4'>No movements.</td></tr>";
  } else {
    inventoryMovementsBody.innerHTML = moves
      .map((move) => {
        return `
          <tr>
            <td>${formatDateTime(move.created_at)}</td>
            <td>${formatQty(move.qty_delta)} ${escapeHtml(move.uom)}</td>
            <td>${escapeHtml(move.reason)}</td>
            <td>${escapeHtml(move.comment || "-")}</td>
          </tr>
        `;
      })
      .join("");
  }
}

async function loadLotsForItem(itemId) {
  movementLot.innerHTML = "<option value=''>Select lot</option>";
  if (!itemId) {
    return;
  }

  const query = buildQuery({ item_id: itemId, page: 1, page_size: 50 });
  const data = await apiRequest(`/lots?${query}`);
  const lots = data.items || [];
  lots.forEach((lot) => {
    const option = document.createElement("option");
    option.value = lot.id;
    option.textContent = `${lot.instance_sku} (${lot.lot_code})`;
    movementLot.appendChild(option);
  });
}

async function loadMovements(page = state.pages.movements) {
  const query = buildQuery({
    search: movementSearch.value.trim(),
    reason: movementFilterReason.value,
    page,
    page_size: 50,
  });
  const data = await apiRequest(`/movements?${query}`);
  const items = data.items || [];
  state.pages.movements = data.page;

  if (items.length === 0) {
    movementsTableBody.innerHTML = "<tr><td colspan='6'>No movements.</td></tr>";
  } else {
    movementsTableBody.innerHTML = items
      .map((move) => {
        return `
          <tr>
            <td>${formatDateTime(move.created_at)}</td>
            <td>${escapeHtml(move.item_product_code)}</td>
            <td>${escapeHtml(move.template_name)}</td>
            <td>${formatQty(move.qty_delta)} ${escapeHtml(move.uom)}</td>
            <td>${escapeHtml(move.reason)}</td>
            <td>${escapeHtml(move.comment || "-")}</td>
          </tr>
        `;
      })
      .join("");
  }

  updatePager("movements", data.page, data.page_size, data.total);
}

async function loadOrders(page = state.pages.orders) {
  const query = buildQuery({
    search: orderSearch.value.trim(),
    status_filter: orderStatusFilter.value,
    page,
    page_size: 25,
  });
  const data = await apiRequest(`/orders?${query}`);
  const items = data.items || [];
  state.pages.orders = data.page;

  if (items.length === 0) {
    ordersTableBody.innerHTML = "<tr><td colspan='5'>No orders.</td></tr>";
  } else {
    ordersTableBody.innerHTML = items
      .map((order) => {
        const allocatedLabel = `${formatQty(order.qty_allocated)} / ${formatQty(
          order.qty_requested
        )}`;
        return `
          <tr>
            <td>${escapeHtml(order.order_number)}</td>
            <td>${escapeHtml(order.status)}</td>
            <td>${escapeHtml(String(order.line_count))}</td>
            <td>${escapeHtml(allocatedLabel)}</td>
            <td><button type="button" class="ghost" data-order-id="${order.id}">View</button></td>
          </tr>
        `;
      })
      .join("");
  }

  ordersTableBody.querySelectorAll("[data-order-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const orderId = Number(button.dataset.orderId);
      loadOrderDetail(orderId);
    });
  });

  updatePager("orders", data.page, data.page_size, data.total);
}

async function loadOrderDetail(orderId) {
  if (!orderId) {
    orderDetailTitle.textContent = "Select an order";
    orderLinesBody.innerHTML = "";
    return;
  }
  const data = await apiRequest(`/orders/${orderId}`);
  state.activeOrderId = orderId;
  orderDetailTitle.textContent = `Order ${data.order_number} (${data.status})`;

  const canWrite = Boolean(state.user && state.user.role !== "VIEWER");
  const lines = data.lines || [];

  if (lines.length === 0) {
    orderLinesBody.innerHTML = "<tr><td colspan='6'>No lines yet.</td></tr>";
  } else {
    orderLinesBody.innerHTML = lines
      .map((line) => {
        const remaining = Number(line.qty_requested) - Number(line.qty_allocated);
        const available = Number(line.available);
        const disableAllocate = remaining <= 0 || available <= 0;
        const allocateButton = canWrite
          ? `<button type="button" class="ghost" data-allocate-line="${line.id}" data-order-id="${data.id}" data-remaining="${remaining}" data-available="${available}" ${disableAllocate ? "disabled" : ""}>Allocate</button>`
          : "";

        return `
          <tr>
            <td>${escapeHtml(line.item_product_code)}</td>
            <td>${escapeHtml(line.template_name)}</td>
            <td>${formatQty(line.qty_requested)}</td>
            <td>${formatQty(line.qty_allocated)}</td>
            <td>${formatQty(line.available)}</td>
            <td>${allocateButton || "-"}</td>
          </tr>
        `;
      })
      .join("");
  }

  orderLinesBody.querySelectorAll("[data-allocate-line]").forEach((button) => {
    button.addEventListener("click", async () => {
      const lineId = Number(button.dataset.allocateLine);
      const orderIdValue = Number(button.dataset.orderId);
      const remaining = Number(button.dataset.remaining);
      const available = Number(button.dataset.available);

      if (remaining <= 0) {
        showToast("Nothing left to allocate.");
        return;
      }

      const raw = window.prompt(
        `Allocate quantity (blank for remaining ${remaining}):`
      );
      if (raw === null) {
        return;
      }

      let qty = null;
      if (raw.trim() !== "") {
        qty = Number(raw);
        if (Number.isNaN(qty) || qty <= 0) {
          showToast("Allocation must be a positive number.");
          return;
        }
        if (qty > remaining) {
          showToast("Allocation exceeds line quantity.");
          return;
        }
        if (qty > available) {
          showToast("Allocation exceeds available stock.");
          return;
        }
      } else if (remaining > available) {
        showToast("Remaining quantity exceeds available stock.");
        return;
      }

      await apiRequest(`/orders/${orderIdValue}/allocate`, {
        method: "POST",
        body: {
          line_id: lineId,
          qty: qty,
        },
      });
      await loadOrderDetail(orderIdValue);
      await loadOrders();
      await loadInventory();
    });
  });
}

function updateMovementReasons() {
  const type = movementType.value;
  const options = movementReasonOptions[type] || ["RECEIPT"];
  movementReason.innerHTML = options
    .map((reason) => `<option value="${reason}">${reason}</option>`)
    .join("");

  if (type === "adjustment") {
    movementComment.placeholder = "Adjustment note (required)";
  } else {
    movementComment.placeholder = "Comment";
  }
}

function resetMovementForm() {
  movementForm.reset();
  movementItemMeta.textContent = "No item selected.";
  movementItemSearch.value = "";
  movementItemSearch.dataset.itemId = "";
  movementLot.disabled = true;
  lotToggle.disabled = true;
  lotCreate.classList.add("is-hidden");
  movementLot.innerHTML = "<option value=''>Select lot</option>";
  updateMovementReasons();
  if (medicalTraceability) {
    movementQty.value = "1";
  }
}

function safeLoad(loader, label) {
  loader().catch((error) => {
    showToast(`${label}: ${error.message}`);
  });
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearStatus(loginStatus);

  try {
    const payload = new URLSearchParams({
      username: loginUsername.value.trim(),
      password: loginPassword.value,
    });

    const data = await apiRequest("/auth/login", {
      method: "POST",
      body: payload.toString(),
      isForm: true,
    });

    state.token = data.access_token;
    localStorage.setItem("minerva_token", data.access_token);
    await loadSession();
  } catch (error) {
    setStatus(loginStatus, error.message, "error");
  }
});

logoutButton.addEventListener("click", () => {
  clearSession("Signed out.");
});

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    setView(tab.dataset.view);
  });
});

catalogFilter.addEventListener("click", () => {
  state.pages.catalog = 1;
  safeLoad(loadCatalog, "Catalog");
});

inventoryFilter.addEventListener("click", () => {
  state.pages.inventory = 1;
  safeLoad(loadInventory, "Inventory");
});

movementFilter.addEventListener("click", () => {
  state.pages.movements = 1;
  safeLoad(loadMovements, "Movements");
});

orderFilter.addEventListener("click", () => {
  state.pages.orders = 1;
  safeLoad(loadOrders, "Orders");
});

addTemplateSpec.addEventListener("click", () => {
  addTemplateSpecRow();
});

templateForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = templateForm.querySelector("[data-status]");
  clearStatus(status);

  try {
    const payload = {
      name: templateForm.querySelector("[name='name']").value.trim(),
      manufacturer_id: templateForm.querySelector("[name='manufacturer_id']").value || null,
      attribute_specs: null,
      sku_rule: null,
    };

    const skuJson = templateSkuJson.value.trim();
    if (skuJson) {
      const parsedRule = JSON.parse(skuJson);
      if (!parsedRule || typeof parsedRule !== "object" || Array.isArray(parsedRule)) {
        throw new Error("SKU rule JSON must be an object.");
      }
      payload.sku_rule = parsedRule;
    } else {
      payload.sku_rule = collectSkuRule();
    }

    const specsJson = templateSpecsJson.value.trim();
    if (specsJson) {
      const parsedSpecs = JSON.parse(specsJson);
      if (!Array.isArray(parsedSpecs)) {
        throw new Error("Attribute specs JSON must be an array.");
      }
      payload.attribute_specs = parsedSpecs;
    } else {
      payload.attribute_specs = collectTemplateSpecs();
    }

    if (payload.manufacturer_id) {
      payload.manufacturer_id = Number(payload.manufacturer_id);
    }

    await apiRequest("/templates", {
      method: "POST",
      body: payload,
    });

    setStatus(status, "Template created.", "success");
    templateForm.reset();
    templateSpecsContainer.innerHTML = "";
    templateSpecsJson.value = "";
    templateSkuJson.value = "";
    addTemplateSpecRow();
    templateForm.querySelector("[name='sku_separator']").value = "-";
    templateForm.querySelector("[name='sku_version']").value = "1";
    templateForm.querySelector("[name='freeze_existing_skus']").checked = true;
    await loadTemplates();
    await loadCatalog();
  } catch (error) {
    setStatus(status, error.message, "error");
  }
});

itemTemplateSelect.addEventListener("change", async () => {
  const templateId = itemTemplateSelect.value;
  itemAttributesJson.value = "";
  if (!templateId) {
    itemAttributesContainer.innerHTML = "<p class='muted'>Select a template to enter attributes.</p>";
    return;
  }
  try {
    const template = await fetchTemplate(templateId);
    renderAttributeFields(template.attribute_specs || []);
  } catch (error) {
    showToast(error.message);
  }
});

itemForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = itemForm.querySelector("[data-status]");
  clearStatus(status);

  try {
    const templateId = itemTemplateSelect.value;
    if (!templateId) {
      throw new Error("Select a template.");
    }

    let attributes = {};
    if (itemAttributesJson.value.trim()) {
      attributes = JSON.parse(itemAttributesJson.value.trim());
    } else {
      attributes = collectAttributes();
    }

    const payload = {
      uom: itemForm.querySelector("[name='uom']").value.trim(),
      track_lots: itemForm.querySelector("[name='track_lots']").checked,
      attributes,
    };

    await apiRequest(`/templates/${Number(templateId)}/items`, {
      method: "POST",
      body: payload,
    });

    setStatus(status, "Item saved.", "success");
    itemForm.reset();
    if (medicalTraceability) {
      const trackLotsInput = itemForm.querySelector("[name='track_lots']");
      if (trackLotsInput) {
        trackLotsInput.checked = true;
      }
    }
    itemAttributesContainer.innerHTML = "<p class='muted'>Select a template to enter attributes.</p>";
    itemAttributesJson.value = "";
    await loadCatalog();
    await loadInventory();
  } catch (error) {
    setStatus(status, error.message, "error");
  }
});

movementType.addEventListener("change", updateMovementReasons);

lotToggle.addEventListener("click", () => {
  lotCreate.classList.toggle("is-hidden");
});

bindItemSearch(movementItemSearch, movementItemOptions, async (item) => {
  if (!item) {
    movementItemMeta.textContent = "No item selected.";
    movementItemSearch.dataset.itemId = "";
    movementLot.disabled = true;
    lotToggle.disabled = true;
    lotCreate.classList.add("is-hidden");
    movementLot.innerHTML = "<option value=''>Select lot</option>";
    return;
  }

  movementItemMeta.textContent = `${item.product_code} - ${item.template_name}`;
  movementItemSearch.dataset.itemId = item.id;
  const trackLots = item.track_lots;
  movementLot.disabled = !trackLots;
  lotToggle.disabled = !trackLots;
  if (!trackLots) {
    lotCreate.classList.add("is-hidden");
  }
  movementUom.value = item.uom;
  if (trackLots) {
    await loadLotsForItem(item.id);
  }
});

movementForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = movementForm.querySelector("[data-status]");
  clearStatus(status);

  try {
    const itemId = movementItemSearch.dataset.itemId;
    if (!itemId) {
      throw new Error("Select an item.");
    }

    const qty = Number(movementQty.value);
    if (!qty || qty <= 0) {
      throw new Error("Quantity must be greater than zero.");
    }
    if (medicalTraceability && qty !== 1) {
      throw new Error("Medical traceability requires quantity of 1.");
    }

    const type = movementType.value;
    const signedQty = type === "outbound" ? -Math.abs(qty) : Math.abs(qty);

    if (type === "adjustment" && !movementComment.value.trim()) {
      throw new Error("Adjustment requires a comment.");
    }

    let lotId = movementLot.value ? Number(movementLot.value) : null;
    if (!lotCreate.classList.contains("is-hidden") && lotCode.value.trim()) {
      const lotPayload = {
        item_id: Number(itemId),
        lot_code: lotCode.value.trim(),
        supplier_name: lotSupplier.value.trim() || null,
        manufacturing_date: lotMfg.value || null,
        expires_at: lotExp.value || null,
      };
      const lot = await apiRequest("/lots", {
        method: "POST",
        body: lotPayload,
      });
      lotId = lot.id;
    }
    if (medicalTraceability && !lotId) {
      throw new Error("Select or create a lot for item-level traceability.");
    }

    const payload = {
      item_id: Number(itemId),
      lot_id: lotId,
      qty_delta: signedQty,
      uom: movementUom.value.trim(),
      reason: movementReason.value,
      comment: movementComment.value.trim() || null,
    };

    await apiRequest("/movements", {
      method: "POST",
      body: payload,
    });

    setStatus(status, "Movement recorded.", "success");
    resetMovementForm();
    await loadMovements();
    await loadInventory();
    if (state.activeInventoryId === Number(itemId)) {
      await loadInventoryDetail(Number(itemId));
    }
  } catch (error) {
    setStatus(status, error.message, "error");
  }
});

orderForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = orderForm.querySelector("[data-status]");
  clearStatus(status);

  try {
    const payload = {
      order_number: orderNumber.value.trim(),
      notes: orderNotes.value.trim() || null,
    };
    const order = await apiRequest("/orders", {
      method: "POST",
      body: payload,
    });

    setStatus(status, "Order created.", "success");
    orderForm.reset();
    await loadOrders();
    await loadOrderDetail(order.id);
  } catch (error) {
    setStatus(status, error.message, "error");
  }
});

bindItemSearch(orderItemSearch, orderItemOptions, (item) => {
  if (item) {
    orderItemSearch.dataset.itemId = item.id;
  } else {
    orderItemSearch.dataset.itemId = "";
  }
});

orderLineForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const status = orderLineForm.querySelector("[data-status]");
  clearStatus(status);

  try {
    if (!state.activeOrderId) {
      throw new Error("Select an order first.");
    }

    const itemId = orderItemSearch.dataset.itemId;
    if (!itemId) {
      throw new Error("Select an item.");
    }

    const qty = Number(orderItemQty.value);
    if (!qty || qty <= 0) {
      throw new Error("Quantity must be greater than zero.");
    }

    const payload = {
      item_id: Number(itemId),
      qty_requested: qty,
    };

    await apiRequest(`/orders/${state.activeOrderId}/lines`, {
      method: "POST",
      body: payload,
    });

    setStatus(status, "Line added.", "success");
    orderLineForm.reset();
    orderItemSearch.dataset.itemId = "";
    await loadOrderDetail(state.activeOrderId);
    await loadOrders();
    await loadInventory();
  } catch (error) {
    setStatus(status, error.message, "error");
  }
});

function init() {
  setupPagers();
  addTemplateSpecRow();
  templateForm.querySelector("[name='sku_separator']").value = "-";
  templateForm.querySelector("[name='sku_version']").value = "1";
  templateForm.querySelector("[name='freeze_existing_skus']").checked = true;
  updateMovementReasons();
  resetMovementForm();
  applyMedicalTraceabilityUI();

  safeLoad(loadManufacturers, "Manufacturers");
  safeLoad(loadTemplates, "Templates");
  safeLoad(loadCatalog, "Catalog");
  safeLoad(loadInventory, "Inventory");
  safeLoad(loadMovements, "Movements");
  safeLoad(loadOrders, "Orders");

  loadSession();
}

init();
