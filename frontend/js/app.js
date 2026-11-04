const $ = (s) => document.querySelector(s);
const API = "";
let token = localStorage.getItem("civic_token");
let role = localStorage.getItem("civic_role");
let currentName = localStorage.getItem("civic_name");
let allRows = [], workers = [], departments = [];

async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const activeToken = token || localStorage.getItem("civic_token");
  const defaultHeaders = {
    ...(activeToken ? { Authorization: `Bearer ${activeToken}` } : {})
  };
  if (!isFormData) {
    defaultHeaders["Content-Type"] = "application/json";
  }
  const headers = { ...defaultHeaders, ...(options.headers || {}) };
  const response = await fetch(API + path, { ...options, headers });
  let data;
  try {
    data = await response.json();
  } catch {
    const rawText = await response.text().catch(() => "");
    data = { detail: rawText || "Server error" };
  }
  if (!response.ok) {
    let errorMsg = "Request failed";
    if (typeof data.detail === "string") {
      errorMsg = data.detail;
    } else if (Array.isArray(data.detail)) {
      errorMsg = data.detail.map(d => d.msg || JSON.stringify(d)).join("; ");
    } else if (data.message) {
      errorMsg = data.message;
    }
    throw new Error(errorMsg);
  }
  return data;
}

function toast(message){const el=$("#toast");el.textContent=message;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),2800)}
function showMessage(message){$("#authMessage").textContent=message}
function formData(form){return Object.fromEntries(new FormData(form).entries())}
function setSession(data){token=data.token;role=data.role;currentName=data.name;localStorage.setItem("civic_token",token);localStorage.setItem("civic_role",role);localStorage.setItem("civic_name",currentName);renderApp()}
function logout(){["civic_token","civic_role","civic_name"].forEach(k=>localStorage.removeItem(k));token=null;role=null;currentName=null;renderApp()}
function renderApp(){
  $("#authView").classList.toggle("hidden",!!token);
  $("#citizenView").classList.toggle("hidden",!(token&&role==="citizen"));
  $("#adminView").classList.toggle("hidden",!(token&&role==="admin"));
  $("#logoutBtn").classList.toggle("hidden",!token);
  if(token&&role==="citizen"){ $("#citizenName").textContent=currentName||"Citizen"; loadMine(); }
  if(token&&role==="admin") loadAdmin();
}
let currentLoginRole = "citizen";

function switchTab(tabName) {
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.tab === tabName));
  $("#loginForm").classList.toggle("hidden", tabName !== "login");
  $("#registerForm").classList.toggle("hidden", tabName !== "register");
  showMessage("");
}

function bindLinkNav() {
  const toReg = $("#toRegisterLink");
  if (toReg) {
    toReg.onclick = (e) => {
      e.preventDefault();
      switchTab("register");
    };
  }
}

function setLoginRole(targetRole) {
  currentLoginRole = targetRole;
  document.querySelectorAll(".role-switch-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.loginRole === targetRole);
  });
  $("#loginRoleInput").value = targetRole;
  showMessage("");

  const isCitizen = targetRole === "citizen";
  $("#authTabs").classList.toggle("hidden", !isCitizen);

  if (isCitizen) {
    $("#loginTitle").textContent = "Citizen sign in";
    $("#loginSubtitle").textContent = "Sign in to report waterlogging and track resolution in your area.";
    $("#loginIdentifierText").textContent = "Email address";
    $("#loginIdentifierInput").type = "email";
    $("#loginIdentifierInput").placeholder = "you@example.com";
    $("#loginSubmitBtn").textContent = "Sign in as Citizen";
    $("#loginHint").innerHTML = 'Need to report an issue? <a href="#" id="toRegisterLink" class="inline-link">Create a citizen account</a>';
    bindLinkNav();
  } else {
    switchTab("login");
    $("#loginTitle").textContent = "Department Officer sign in";
    $("#loginSubtitle").textContent = "Sign in to access municipal control, review complaints, and assign workers.";
    $("#loginIdentifierText").textContent = "Officer username / ID";
    $("#loginIdentifierInput").type = "text";
    $("#loginIdentifierInput").placeholder = "admin";
    $("#loginSubmitBtn").textContent = "Sign in as Department Officer";
    $("#loginHint").innerHTML = 'Demo credentials: <b>admin</b> / <b>Admin@12345</b>';
  }
}

document.querySelectorAll(".role-switch-btn").forEach(btn => {
  btn.addEventListener("click", () => setLoginRole(btn.dataset.loginRole));
});

document.querySelectorAll(".tab").forEach(btn => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));

const toLoginLink = $("#toLoginLink");
if (toLoginLink) {
  toLoginLink.onclick = (e) => {
    e.preventDefault();
    switchTab("login");
  };
}
bindLinkNav();

$("#loginForm").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const res = await request("/api/login", { method: "POST", body: JSON.stringify(formData(e.target)) });
    setSession(res);
    toast(res.role === "admin" ? `Welcome, Officer ${res.name}!` : `Welcome back, ${res.name}!`);
  } catch (err) {
    showMessage(err.message);
  }
});
$("#registerForm").addEventListener("submit",async e=>{e.preventDefault();try{setSession(await request("/api/register",{method:"POST",body:JSON.stringify(formData(e.target))}));toast("Account created successfully")}catch(err){showMessage(err.message)}});
$("#logoutBtn").onclick=logout;
$("#showComplaintForm").onclick=()=>$("#complaintFormCard").classList.remove("hidden");
$("#closeComplaintForm").onclick=()=>$("#complaintFormCard").classList.add("hidden");

// Auto-detect Location
const detectBtn = $("#detectLocationBtn");
const detectBtnText = $("#detectBtnText");
const locationInput = $("#complaintLocation");
const locationStatus = $("#locationStatus");

if (detectBtn) {
  detectBtn.addEventListener("click", () => {
    if (!navigator.geolocation) {
      toast("Geolocation is not supported by your browser");
      if (locationStatus) {
        locationStatus.className = "field-hint-text error";
        locationStatus.textContent = "Geolocation is not supported by your browser.";
      }
      return;
    }

    detectBtn.disabled = true;
    if (detectBtnText) detectBtnText.textContent = "Acquiring GPS...";
    if (locationStatus) {
      locationStatus.className = "field-hint-text loading";
      locationStatus.textContent = "Connecting to device GPS...";
    }

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude.toFixed(6);
        const lon = pos.coords.longitude.toFixed(6);
        if (locationStatus) {
          locationStatus.textContent = `GPS: ${lat}, ${lon} · Resolving street address...`;
        }

        try {
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`, {
            headers: { "Accept-Language": "en" }
          });
          if (res.ok) {
            const data = await res.json();
            const a = data.address || {};
            const parts = [
              a.road || a.street || a.neighbourhood || a.suburb,
              a.residential || a.subdistrict || a.city_district,
              a.city || a.town || a.village || a.county,
              a.postcode
            ].filter(Boolean);
            const address = parts.length ? parts.join(", ") : data.display_name;
            locationInput.value = address || `Lat: ${lat}, Lon: ${lon}`;
            if (locationStatus) {
              locationStatus.className = "field-hint-text success";
              locationStatus.textContent = `✓ Auto-detected: ${lat}, ${lon}`;
            }
            toast("Location auto-detected!");
          } else {
            locationInput.value = `GPS: ${lat}, ${lon}`;
            if (locationStatus) {
              locationStatus.className = "field-hint-text success";
              locationStatus.textContent = `✓ Coordinates captured: ${lat}, ${lon}`;
            }
            toast("GPS coordinates captured");
          }
        } catch {
          locationInput.value = `GPS: ${lat}, ${lon}`;
          if (locationStatus) {
            locationStatus.className = "field-hint-text success";
            locationStatus.textContent = `✓ Coordinates captured: ${lat}, ${lon}`;
          }
          toast("GPS coordinates captured");
        } finally {
          detectBtn.disabled = false;
          if (detectBtnText) detectBtnText.textContent = "Auto-detect location";
        }
      },
      (err) => {
        let msg = "Could not access location.";
        if (err.code === 1) msg = "Location permission denied. Please allow location access or type manually.";
        else if (err.code === 2) msg = "Location unavailable. Please enter manually.";
        else if (err.code === 3) msg = "Location request timed out. Please enter manually.";
        if (locationStatus) {
          locationStatus.className = "field-hint-text error";
          locationStatus.textContent = msg;
        }
        toast(msg);
        detectBtn.disabled = false;
        if (detectBtnText) detectBtnText.textContent = "Auto-detect location";
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  });
}

// Photo Upload Handling
const photoInput = $("#complaintPhotoInput");
const photoDropArea = $("#photoDropArea");
const photoPrompt = $("#photoPrompt");
const photoPreviewWrap = $("#photoPreviewWrap");
const photoPreviewImg = $("#photoPreviewImg");
const photoFileName = $("#photoFileName");
const removePhotoBtn = $("#removePhotoBtn");

function handlePhotoFile(file) {
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    toast("Please choose an image file (PNG, JPG, WEBP)");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    toast("Image must be smaller than 10MB");
    return;
  }
  photoPreviewImg.src = URL.createObjectURL(file);
  photoFileName.textContent = file.name;
  photoPrompt.classList.add("hidden");
  photoPreviewWrap.classList.remove("hidden");
}

function clearPhoto() {
  if (photoInput) photoInput.value = "";
  if (photoPreviewImg) photoPreviewImg.src = "";
  if (photoFileName) photoFileName.textContent = "";
  if (photoPreviewWrap) photoPreviewWrap.classList.add("hidden");
  if (photoPrompt) photoPrompt.classList.remove("hidden");
}

if (photoDropArea) {
  photoDropArea.addEventListener("click", (e) => {
    if (e.target.id === "removePhotoBtn" || e.target.closest("#removePhotoBtn")) {
      return;
    }
    photoInput.click();
  });

  photoDropArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    photoDropArea.classList.add("dragover");
  });
  photoDropArea.addEventListener("dragleave", () => {
    photoDropArea.classList.remove("dragover");
  });
  photoDropArea.addEventListener("drop", (e) => {
    e.preventDefault();
    photoDropArea.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      photoInput.files = e.dataTransfer.files;
      handlePhotoFile(e.dataTransfer.files[0]);
    }
  });
}

if (photoInput) {
  photoInput.addEventListener("change", () => {
    if (photoInput.files && photoInput.files[0]) {
      handlePhotoFile(photoInput.files[0]);
    }
  });
}

if (removePhotoBtn) {
  removePhotoBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    clearPhoto();
  });
}

// Photo Lightbox Modal
window.openPhotoModal = function(src, title) {
  const modal = $("#photoModal");
  if (!modal) return;
  $("#photoModalImg").src = src;
  $("#photoModalTitle").textContent = title || "Waterlogging Site Photo";
  modal.classList.remove("hidden");
};

window.closePhotoModal = function() {
  const modal = $("#photoModal");
  if (!modal) return;
  modal.classList.add("hidden");
  $("#photoModalImg").src = "";
};

const closePhotoBtn = $("#closePhotoModalBtn");
if (closePhotoBtn) closePhotoBtn.onclick = window.closePhotoModal;
const photoBackdrop = $("#photoModalBackdrop");
if (photoBackdrop) photoBackdrop.onclick = window.closePhotoModal;
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") window.closePhotoModal();
});

// Submit Complaint
$("#complaintForm").addEventListener("submit", async e => {
  e.preventDefault();
  const submitBtn = $("#submitComplaintBtn");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting complaint...";
  }
  try {
    const formData = new FormData(e.target);
    const file = formData.get("photo");
    if (file && (!file.name || file.size === 0)) {
      formData.delete("photo");
    }
    await request("/api/complaints", {
      method: "POST",
      body: formData
    });
    e.target.reset();
    clearPhoto();
    if (locationStatus) {
      locationStatus.textContent = "";
      locationStatus.className = "field-hint-text";
    }
    $("#complaintFormCard").classList.add("hidden");
    toast("Complaint submitted successfully!");
    loadMine();
  } catch (err) {
    toast(err.message);
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit complaint";
    }
  }
});

$("#refreshCitizen").onclick = loadMine;

function badge(status) {
  return `<span class="status ${status.replace(" ", ".")}">${status}</span>`;
}
function empty(text) {
  return `<div class="empty">${text}</div>`;
}

function renderRows(rows, admin = false) {
  if (!rows.length) return empty("No complaints found yet.");
  return `<table>
    <thead>
      <tr>
        <th>ID</th>
        ${admin ? "<th>Citizen</th>" : ""}
        <th>Location</th>
        <th>Photo</th>
        <th>Priority</th>
        <th>Status</th>
        <th>Assigned worker</th>
        <th>Date</th>
        ${admin ? "<th>Manage</th>" : ""}
      </tr>
    </thead>
    <tbody>
      ${rows.map(c => `<tr>
        <td>#${c.complaint_id}</td>
        ${admin ? `<td>${escapeHtml(c.citizen_name)}</td>` : ""}
        <td title="${escapeHtml(c.description)}">${escapeHtml(c.location)}</td>
        <td>
          ${c.photo_path ? `<button type="button" class="photo-badge-btn" onclick="openPhotoModal('${escapeHtml(c.photo_path)}', 'Complaint #${c.complaint_id} · ${escapeHtml(c.location)}')"><img src="${escapeHtml(c.photo_path)}" class="table-photo-thumb" alt="Thumbnail"> View</button>` : `<span class="no-photo">—</span>`}
        </td>
        <td class="priority">${c.priority}</td>
        <td>${badge(c.status)}</td>
        <td>${escapeHtml(c.worker_name || "Not assigned")}</td>
        <td>${c.complaint_date ? new Date(c.complaint_date).toLocaleDateString() : "—"}</td>
        ${admin ? `<td>
          <select class="action-select" data-status="${c.complaint_id}">
            <option ${c.status === "Pending" ? "selected" : ""}>Pending</option>
            <option ${c.status === "In Progress" ? "selected" : ""}>In Progress</option>
            <option ${c.status === "Resolved" ? "selected" : ""}>Resolved</option>
          </select>
          <select class="action-select" data-assign="${c.complaint_id}">
            <option value="">Assign worker</option>
            ${workers.map(w => `<option value="${w.worker_id}" ${c.worker_name === w.worker_name ? "selected" : ""}>${escapeHtml(w.worker_name)}</option>`).join("")}
          </select>
        </td>` : ""}
      </tr>`).join("")}
    </tbody>
  </table>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

async function loadMine() {
  try {
    const rows = await request("/api/complaints/my");
    $("#myComplaints").innerHTML = renderRows(rows);
    $("#myTotal").textContent = rows.length;
    $("#myProgress").textContent = rows.filter(x => x.status === "In Progress").length;
    $("#myResolved").textContent = rows.filter(x => x.status === "Resolved").length;
  } catch (e) {
    toast(e.message);
  }
}

async function loadAdmin() {
  try {
    const [stats, rows, w, d] = await Promise.all([
      request("/api/dashboard"),
      request("/api/complaints"),
      request("/api/workers"),
      request("/api/departments")
    ]);
    allRows = rows;
    workers = w;
    departments = d;
    $("#statTotal").textContent = stats.total;
    $("#statPending").textContent = stats.Pending;
    $("#statProgress").textContent = stats["In Progress"];
    $("#statResolved").textContent = stats.Resolved;
    renderAdminTable();
    $("#workersList").innerHTML = w.map(x => `<div><b>${escapeHtml(x.worker_name)}</b> · ${escapeHtml(x.department || "No department")} · ${escapeHtml(x.phone)}</div>`).join("") || empty("No workers added.");
    $("#departmentsList").innerHTML = d.map(x => `<div>${escapeHtml(x.department_name)}</div>`).join("") || empty("No departments.");
    $("#departmentSelect").innerHTML = d.map(x => `<option value="${x.department_id}">${escapeHtml(x.department_name)}</option>`).join("");
  } catch (e) {
    toast(e.message);
  }
}

function renderAdminTable() {
  const q = $("#adminSearch").value.toLowerCase();
  const rows = allRows.filter(c => String(c.complaint_id).includes(q) || c.location.toLowerCase().includes(q));
  $("#allComplaints").innerHTML = renderRows(rows, true);
  document.querySelectorAll("[data-status]").forEach(el => el.onchange = async () => {
    try {
      await request(`/api/complaints/${el.dataset.status}/status`, {
        method: "PUT",
        body: JSON.stringify({ status: el.value })
      });
      toast("Complaint status updated");
      loadAdmin();
    } catch (e) {
      toast(e.message);
    }
  });
  document.querySelectorAll("[data-assign]").forEach(el => el.onchange = async () => {
    if (!el.value) return;
    try {
      await request("/api/assignments", {
        method: "POST",
        body: JSON.stringify({ complaint_id: Number(el.dataset.assign), worker_id: Number(el.value) })
      });
      toast("Worker assigned");
      loadAdmin();
    } catch (e) {
      toast(e.message);
    }
  });
}

$("#adminSearch").addEventListener("input", renderAdminTable);
$("#refreshAdmin").onclick = loadAdmin;
$("#workerForm").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    await request("/api/workers", {
      method: "POST",
      body: JSON.stringify({ ...formData(e.target), department_id: Number(formData(e.target).department_id) })
    });
    e.target.reset();
    toast("Worker added");
    loadAdmin();
  } catch (err) {
    toast(err.message);
  }
});
$("#departmentForm").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    await request("/api/departments", {
      method: "POST",
      body: JSON.stringify(formData(e.target))
    });
    e.target.reset();
    toast("Department added");
    loadAdmin();
  } catch (err) {
    toast(err.message);
  }
});
renderApp();
