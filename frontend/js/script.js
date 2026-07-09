// Intercept all fetch requests to inject JWT token and handle 401 Unauthorized globally
const originalFetch = window.fetch;
window.fetch = async function(input, init) {
    // 1. Resolve URL string
    let urlString = "";
    if (typeof input === 'string') {
        urlString = input;
    } else if (input && input.url) {
        urlString = input.url;
    } else if (input && typeof input.toString === 'function') {
        urlString = input.toString();
    }

    // 2. Inject Authorization header if it is an API call, not login/register, and token exists
    const token = localStorage.getItem("access_token");
    if (token && urlString.includes("/api/") && !urlString.includes("/api/auth/login") && !urlString.includes("/api/auth/register")) {
        init = init || {};
        init.headers = init.headers || {};
        
        // Handle Headers object, Array, or plain object
        if (init.headers instanceof Headers) {
            if (!init.headers.has("Authorization")) {
                init.headers.set("Authorization", `Bearer ${token}`);
            }
        } else if (Array.isArray(init.headers)) {
            const hasAuth = init.headers.some(h => h[0].toLowerCase() === "authorization");
            if (!hasAuth) {
                init.headers.push(["Authorization", `Bearer ${token}`]);
            }
        } else {
            // standard object
            let hasAuth = false;
            for (const key in init.headers) {
                if (key.toLowerCase() === "authorization") {
                    hasAuth = true;
                    break;
                }
            }
            if (!hasAuth) {
                init.headers["Authorization"] = `Bearer ${token}`;
            }
        }
    }

    // 3. Perform original fetch
    const response = await originalFetch(input, init);

    // 4. Handle 401 globally
    if (response.status === 401) {
        if (!urlString.includes('/api/auth/login')) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("username");
            window.location.href = "index.html";
        }
    }
    return response;
};


// ConstructAI ERP - Core Client Script
// API_BASE is derived from API_BASE_URL configured in api.js
const API_BASE = API_BASE_URL.endsWith('/api') ? API_BASE_URL.slice(0, -4) : API_BASE_URL;

// Utility: Decode JWT Payload to resolve user roles
const decodeToken = (token) => {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(c => {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
};

// Global headers builder
function getAuthHeaders() {
    const token = localStorage.getItem("access_token");
    return {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
    };
}

// ========================================================
// 1. AUTHENTICATION & LOGIN LOGIC (index.html)
// ========================================================
if (document.getElementById("login-form")) {
    document.getElementById("login-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("login-username").value.trim();
        const password = document.getElementById("login-password").value;
        const submitBtn = document.getElementById("btn-login-submit");
        
        hideAuthAlert();
        setBtnLoading(submitBtn, "Logging in...");

        try {
            const res = await fetch(`${API_BASE}/api/auth/login/json`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Authentication failed.");

            // Store credentials
            localStorage.setItem("access_token", data.access_token);
            localStorage.setItem("username", username);
            
            // Redirect
            window.location.href = "dashboard.html";
        } catch (err) {
            showAuthAlert(err.message);
            setBtnNormal(submitBtn, "Log in");
        }
    });
}

if (document.getElementById("signup-form")) {
    document.getElementById("signup-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("signup-email").value.trim();
        const username = document.getElementById("signup-username").value.trim();
        const password = document.getElementById("signup-password").value;
        const role = document.getElementById("signup-role").value;
        const submitBtn = document.getElementById("btn-signup-submit");

        hideAuthAlert();
        setBtnLoading(submitBtn, "Creating account...");

        try {
            const res = await fetch(`${API_BASE}/api/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, username, password, role })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Registration failed.");

            alert("Account registered successfully! You can now log in.");
            toggleAuthMode("login");
        } catch (err) {
            showAuthAlert(err.message);
        } finally {
            setBtnNormal(submitBtn, "Sign up");
        }
    });
}

// Helpers for Auth Page
function togglePasswordVisibility(fieldId, iconElement) {
    const input = document.getElementById(fieldId);
    const svg = iconElement.querySelector(".eye-icon");
    if (input.type === "password") {
        input.type = "text";
        svg.innerHTML = `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>`;
    } else {
        input.type = "password";
        svg.innerHTML = `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>`;
    }
}

function toggleAuthMode(mode) {
    const login = document.getElementById("login-container");
    const signup = document.getElementById("signup-container");
    const welcome = document.querySelector(".welcome-text");
    hideAuthAlert();

    if (mode === "signup") {
        login.classList.add("hidden");
        signup.classList.remove("hidden");
        welcome.textContent = "Start Journey";
    } else {
        signup.classList.add("hidden");
        login.classList.remove("hidden");
        welcome.textContent = "Welcome Back";
    }
}

function showAuthAlert(msg) {
    const alertBox = document.getElementById("auth-alert");
    document.getElementById("auth-alert-msg").textContent = msg;
    alertBox.style.display = "flex";
}

function hideAuthAlert() {
    document.getElementById("auth-alert").style.display = "none";
}

function setBtnLoading(btn, text) {
    btn.disabled = true;
    btn.textContent = text;
}

function setBtnNormal(btn, text) {
    btn.disabled = false;
    btn.textContent = text;
}

// ========================================================
// 2. DASHBOARD SHELL & TAB CONTROLLER (dashboard.html)
// ========================================================
let activeInvoiceId = null; // Track parsed invoice currently loaded in parser panel
let currentCharts = {}; // Save Chart.js instances

if (document.getElementById("view-dashboard")) {
    // Authorization Check
    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "index.html";
    }

    // Set User Profile headers
    const username = localStorage.getItem("username") || "Employee";
    const decoded = decodeToken(token);
    const role = decoded ? decoded.sub : "EMPLOYEE"; // Token subject holds sub, backend resolves roles
    
    // Set HTML profile values
    document.getElementById("user-display-name").textContent = username;
    document.getElementById("avatar-letters").textContent = username.substring(0,2).toUpperCase();
    
    // We can fetch system configuration to retrieve the active role details
    fetchUserProfile();

    // Bind URL hash switches
    window.addEventListener("hashchange", handleHashRoute);
    
    // Initial load
    handleHashRoute();
    setupDragAndDrop();
    loadDashboardKPIs();
    
    // Load Settings
    loadSystemSettings();
}

function handleHashRoute() {
    const hash = window.location.hash.substring(1) || "dashboard";
    switchTab(hash);
}

function switchTab(tabId) {
    // 1. Highlight menu item
    document.querySelectorAll(".menu-item").forEach(item => {
        item.classList.remove("active");
        if (item.getAttribute("href") === `#${tabId}`) {
            item.classList.add("active");
        }
    });

    // 2. Toggle visible viewport panel
    document.querySelectorAll(".view-section").forEach(sec => {
        sec.classList.add("hidden");
    });
    
    const activeSec = document.getElementById(`view-${tabId}`);
    if (activeSec) {
        activeSec.classList.remove("hidden");
    }

    // Auto-close sidebar on mobile after tab switch
    const sidebar = document.querySelector(".sidebar");
    if (sidebar) {
        sidebar.classList.remove("open");
    }

    // 3. Trigger specific tab loaders
    if (tabId === "dashboard") {
        loadDashboardKPIs();
    } else if (tabId === "database") {
        loadDatabaseInvoices();
    } else if (tabId === "vendors") {
        loadVendors();
    } else if (tabId === "analytics") {
        loadAnalytics();
    } else if (tabId === "logs") {
        loadAuditLogs();
    } else if (tabId === "settings") {
        loadSystemSettings();
    }
}

async function fetchUserProfile() {
    try {
        const res = await fetch(`${API_BASE}/api/settings`, { headers: getAuthHeaders() });
        const data = await res.json();
        // Resolve user role based on token decoding or metadata mapping
        const token = localStorage.getItem("access_token");
        const decoded = decodeToken(token);
        // Note: For simplicity, the seed script hashes roles. We fetch logs to verify role name or default to token
        // Let's call vendors list. If it throws 403 on admin routes, role is Employee.
        // Let's decode custom role if present
        const checkRole = decoded ? decoded.role : "EMPLOYEE"; // backend can pack claims
        // Let's ask API to return profile if needed. We query user-display-role and update it:
        // By default, if user is admin, they are ADMIN
        const user = localStorage.getItem("username");
        if (user === "admin") {
            document.getElementById("user-display-role").textContent = "ADMIN";
            document.getElementById("settings-role").textContent = "ADMIN";
        } else {
            document.getElementById("user-display-role").textContent = "EMPLOYEE";
            document.getElementById("settings-role").textContent = "EMPLOYEE";
        }
    } catch(e) {}
}

function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    window.location.href = "index.html";
}

// ========================================================
// 3. DASHBOARD TAB VIEW & KPIS
// ========================================================
async function loadDashboardKPIs() {
    try {
        const res = await fetch(`${API_BASE}/api/analytics`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error("Could not load metrics.");
        const data = await res.json();

        // Bind KPIs
        document.getElementById("kpi-total-invoices").textContent = data.kpis.total_invoices;
        document.getElementById("kpi-processed-invoices").textContent = data.kpis.processed_invoices;
        document.getElementById("kpi-pending-review").textContent = data.kpis.pending_review;
        document.getElementById("kpi-total-expense").textContent = data.kpis.total_expense;
        document.getElementById("kpi-total-vendors").textContent = data.kpis.total_vendors;
        document.getElementById("kpi-accuracy").textContent = data.kpis.avg_accuracy;

        // Load recent activity table
        const invoicesRes = await fetch(`${API_BASE}/api/invoices`, { headers: getAuthHeaders() });
        const invoices = await invoicesRes.json();
        
        const tbody = document.getElementById("recent-invoices-tbody");
        tbody.innerHTML = "";
        
        // Take latest 5
        const sorted = invoices.sort((a,b) => b.id - a.id).slice(0, 5);
        if (sorted.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--color-text-muted);">No invoice records found in ERP.</td></tr>`;
            return;
        }

        sorted.forEach(inv => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${inv.vendor_name}</strong></td>
                <td><code>${inv.invoice_number}</code></td>
                <td>${inv.date || "N/A"}</td>
                <td>${inv.total_amount}</td>
                <td><span class="status-badge ${inv.status.toLowerCase().replace(" ", "_")}">${inv.status}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error(e);
    }
}

// ========================================================
// 4. AI PARSER CONTROLS
// ========================================================
function setupDragAndDrop() {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");

    if (!dropZone) return;

    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        }, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length) {
            handleFileUpload(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (fileInput.files.length) {
            handleFileUpload(fileInput.files[0]);
        }
    });
}

async function handleFileUpload(file) {
    const progress = document.getElementById("parser-progress");
    const bar = document.getElementById("progress-bar-fill");
    const log = document.getElementById("progress-status-log");
    const percentText = document.getElementById("progress-percent");
    const filenameText = document.getElementById("progress-filename");
    
    const placeholder = document.getElementById("parser-result-placeholder");
    const card = document.getElementById("extraction-card");

    // Reset panel view
    placeholder.classList.remove("hidden");
    card.classList.add("hidden");

    // Setup Progress Bar UI
    progress.classList.remove("hidden");
    filenameText.textContent = file.name;
    bar.style.width = "0%";
    percentText.textContent = "0%";
    log.textContent = "Starting ingestion stream...";

    // Simulated progress steps for beautiful UI micro-animation
    let step = 0;
    const interval = setInterval(() => {
        step += 15;
        if (step <= 90) {
            bar.style.width = `${step}%`;
            percentText.textContent = `${step}%`;
            if (step === 30) log.textContent = "Scanning documents structure...";
            if (step === 60) log.textContent = "Connecting Generative AI models...";
            if (step === 90) log.textContent = "Reconstructing items matrix JSON...";
        }
    }, 300);

    const formData = new FormData();
    formData.append("file", file);

    try {
        const token = localStorage.getItem("access_token");
        const res = await fetch(`${API_BASE}/api/invoices/upload`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`
            },
            body: formData
        });

        clearInterval(interval);
        
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "AI Extraction service failed.");
        }

        // Fill progress
        bar.style.width = "100%";
        percentText.textContent = "100%";
        log.textContent = "Success! Saved to ERP ledger.";

        const invoice = await res.json();
        setTimeout(() => {
            progress.classList.add("hidden");
            displayExtractionResult(invoice);
        }, 800);

    } catch (e) {
        clearInterval(interval);
        progress.classList.add("hidden");
        alert(e.message);
    }
}

function displayExtractionResult(invoice) {
    activeInvoiceId = invoice.id;
    
    document.getElementById("parser-result-placeholder").classList.add("hidden");
    document.getElementById("extraction-card").classList.remove("hidden");

    // Populate Fields
    document.getElementById("ext-vendor-title").textContent = invoice.vendor_name;
    document.getElementById("ext-confidence").textContent = invoice.confidence;
    document.getElementById("ext-status").textContent = invoice.status;
    
    // Status color class
    const badge = document.getElementById("ext-status");
    badge.className = `status-badge ${invoice.status.toLowerCase().replace(" ", "_")}`;

    document.getElementById("ext-inv-no").textContent = invoice.invoice_number;
    document.getElementById("ext-date").textContent = invoice.date || "N/A";
    document.getElementById("ext-tax").textContent = invoice.tax_amount;
    document.getElementById("ext-total").textContent = invoice.total_amount;
    document.getElementById("ext-terms").textContent = invoice.payment_terms || "N/A";
    
    // Primary item extracts (guess or use first item)
    if (invoice.items && invoice.items.length) {
        document.getElementById("ext-material").textContent = invoice.items[0].description;
        document.getElementById("ext-qty").textContent = invoice.items[0].quantity;
        document.getElementById("ext-unit-price").textContent = invoice.items[0].unit_price;
    } else {
        document.getElementById("ext-material").textContent = "N/A";
        document.getElementById("ext-qty").textContent = "N/A";
        document.getElementById("ext-unit-price").textContent = "N/A";
    }

    // Populate items list
    const tbody = document.getElementById("ext-items-tbody");
    tbody.innerHTML = "";
    
    if (invoice.items && invoice.items.length) {
        invoice.items.forEach(item => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${item.description}</td>
                <td>${item.quantity || "1"}</td>
                <td>${item.unit_price || "N/A"}</td>
                <td><strong>${item.total_price || "N/A"}</strong></td>
            `;
            tbody.appendChild(tr);
        });
    } else {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center;">No item grid extracted.</td></tr>`;
    }

    // Populate raw logs
    document.getElementById("ext-raw-text").textContent = invoice.raw_text;
    
    // Reset tabs
    toggleResultView('structured');

    // Update ERP Sync Button state depending on status
    const syncBtn = document.getElementById("btn-sync-gateway");
    if (invoice.sync_status === "Synced") {
        syncBtn.disabled = true;
        syncBtn.textContent = "✓ Synced to ERP";
    } else {
        syncBtn.disabled = false;
        syncBtn.textContent = "⚡ Sync to ERP Gateway";
    }
}

function toggleResultView(view) {
    const structView = document.getElementById("result-structured-view");
    const rawView = document.getElementById("result-raw-view");
    const tabStruct = document.getElementById("tab-structured");
    const tabRaw = document.getElementById("tab-raw");

    if (view === 'structured') {
        structView.classList.remove("hidden");
        rawView.classList.add("hidden");
        tabStruct.classList.add("active");
        tabRaw.classList.remove("active");
    } else {
        structView.classList.add("hidden");
        rawView.classList.remove("hidden");
        tabStruct.classList.remove("active");
        tabRaw.classList.add("active");
    }
}

async function syncActiveInvoiceToERP() {
    if (!activeInvoiceId) return;

    try {
        const res = await fetch(`${API_BASE}/api/invoices/${activeInvoiceId}/sync`, {
            method: "POST",
            headers: getAuthHeaders()
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Sync failed.");

        alert(data.message);
        
        // Update UI
        const syncBtn = document.getElementById("btn-sync-gateway");
        syncBtn.disabled = true;
        syncBtn.textContent = "✓ Synced to ERP";

        loadDashboardKPIs();
    } catch (e) {
        alert(e.message);
    }
}

// ========================================================
// 5. ERP DATABASE LISTING (CRUD)
// ========================================================
async function loadDatabaseInvoices() {
    const search = document.getElementById("db-search").value.trim();
    const statusVal = document.getElementById("db-filter-status").value;
    const syncVal = document.getElementById("db-filter-sync").value;

    let url = `${API_BASE}/api/invoices?`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    if (statusVal) url += `status=${encodeURIComponent(statusVal)}&`;

    try {
        const res = await fetch(url, { headers: getAuthHeaders() });
        let invoices = await res.json();

        // Filter by sync manually as backend schema handles standard params
        if (syncVal) {
            invoices = invoices.filter(inv => inv.sync_status === syncVal);
        }

        const tbody = document.getElementById("db-invoices-tbody");
        tbody.innerHTML = "";

        if (invoices.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--color-text-muted); padding: 30px;">No invoices found matching current filter scope.</td></tr>`;
            return;
        }

        invoices.forEach(inv => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><code>#${inv.id}</code></td>
                <td><strong>${inv.vendor_name}</strong></td>
                <td>${inv.date || "N/A"}</td>
                <td>${inv.tax_amount}</td>
                <td><strong>${inv.total_amount}</strong></td>
                <td>${inv.confidence}</td>
                <td><span class="status-badge ${inv.status.toLowerCase().replace(" ", "_")}">${inv.status}</span></td>
                <td><span class="status-badge ${inv.sync_status.toLowerCase()}">${inv.sync_status}</span></td>
                <td>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-sm btn-light" onclick="viewInvoiceDetails(${inv.id})">Details</button>
                        <button class="btn btn-sm btn-light" onclick="syncSpecificInvoice(${inv.id}, '${inv.sync_status}')" ${inv.sync_status === 'Synced' ? 'disabled' : ''}>Sync</button>
                        <button class="btn btn-sm btn-dark" style="background-color: var(--color-danger); color: #ffffff;" onclick="deleteInvoiceRecord(${inv.id})">Delete</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error(e);
    }
}

async function viewInvoiceDetails(id) {
    try {
        const res = await fetch(`${API_BASE}/api/invoices/${id}`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error("Could not fetch invoice details.");
        const inv = await res.json();

        // Populate modal fields
        document.getElementById("details-modal-title").textContent = `Invoice: ${inv.invoice_number}`;
        const statusBadge = document.getElementById("details-modal-status");
        statusBadge.textContent = inv.status;
        statusBadge.className = `status-badge ${inv.status.toLowerCase().replace(" ", "_")}`;

        document.getElementById("details-vendor").textContent = inv.vendor_name;
        document.getElementById("details-inv-no").textContent = inv.invoice_number;
        document.getElementById("details-date").textContent = inv.date || "N/A";
        document.getElementById("details-tax").textContent = inv.tax_amount;
        document.getElementById("details-total").textContent = inv.total_amount;
        document.getElementById("details-confidence").textContent = inv.confidence;
        document.getElementById("details-sync").textContent = inv.sync_status;
        document.getElementById("details-created").textContent = new Date(inv.created_at).toLocaleString();
        
        // Items list
        const tbody = document.getElementById("details-items-tbody");
        tbody.innerHTML = "";
        inv.items.forEach(item => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${item.description}</td>
                <td>${item.quantity || "1"}</td>
                <td>${item.unit_price || "N/A"}</td>
                <td><strong>${item.total_price || "N/A"}</strong></td>
            `;
            tbody.appendChild(tr);
        });

        // Raw text
        document.getElementById("details-raw-text").textContent = inv.raw_text;

        // Show Modal
        document.getElementById("invoice-details-modal").classList.remove("hidden");
    } catch (e) {
        alert(e.message);
    }
}

function hideInvoiceDetailsModal() {
    document.getElementById("invoice-details-modal").classList.add("hidden");
}

async function syncSpecificInvoice(id, syncStatus) {
    if (syncStatus === "Synced") return;
    try {
        const res = await fetch(`${API_BASE}/api/invoices/${id}/sync`, {
            method: "POST",
            headers: getAuthHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Sync failed.");
        alert(data.message);
        loadDatabaseInvoices();
    } catch (e) {
        alert(e.message);
    }
}

async function deleteInvoiceRecord(id) {
    if (!confirm("Are you sure you want to delete this invoice record from the database? This action is permanent and cascades to line items.")) {
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/invoices/${id}`, {
            method: "DELETE",
            headers: getAuthHeaders()
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Delete call failed.");

        alert(data.message || "Successfully deleted record.");
        loadDatabaseInvoices();
        loadDashboardKPIs();
    } catch (e) {
        alert(e.message);
    }
}

// Global search box listener
function handleGlobalSearch(e) {
    if (e.key === "Enter") {
        const query = document.getElementById("global-search").value.trim();
        if (query) {
            // Redirect to database panel, pass search query to input and search
            switchTab("database");
            document.getElementById("db-search").value = query;
            loadDatabaseInvoices();
        }
    }
}

// ========================================================
// 6. VENDOR MANAGEMENT
// ========================================================
async function loadVendors() {
    try {
        const res = await fetch(`${API_BASE}/api/vendors`, { headers: getAuthHeaders() });
        const vendors = await res.json();

        const tbody = document.getElementById("vendors-tbody");
        tbody.innerHTML = "";

        if (vendors.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--color-text-muted);">No vendor records registered.</td></tr>`;
            return;
        }

        vendors.forEach(v => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><code>#${v.id}</code></td>
                <td><strong>${v.vendor_name}</strong></td>
                <td><code>${v.gst_number}</code></td>
                <td>${v.contact}</td>
                <td>${v.total_invoices}</td>
                <td><strong>${v.total_purchase_amount}</strong></td>
                <td>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-sm btn-light" onclick="editVendorProfile(${v.id}, '${v.vendor_name}', '${v.gst_number}', '${v.contact}')">Edit</button>
                        <button class="btn btn-sm btn-dark" style="background-color: var(--color-danger); color: #ffffff;" onclick="deleteVendorProfile(${v.id})">Delete</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error(e);
    }
}

function showAddVendorModal() {
    document.getElementById("vendor-form").reset();
    document.getElementById("vendor-id").value = "";
    document.getElementById("vendor-modal-title").textContent = "New Vendor Profile";
    document.getElementById("vendor-modal").classList.remove("hidden");
}

function hideAddVendorModal() {
    document.getElementById("vendor-modal").classList.add("hidden");
}

function editVendorProfile(id, name, gst, contact) {
    document.getElementById("vendor-id").value = id;
    document.getElementById("vendor-name").value = name;
    document.getElementById("vendor-gst").value = gst;
    document.getElementById("vendor-contact").value = contact;
    document.getElementById("vendor-modal-title").textContent = "Edit Vendor Profile";
    document.getElementById("vendor-modal").classList.remove("hidden");
}

async function handleVendorSubmit(e) {
    e.preventDefault();
    const id = document.getElementById("vendor-id").value;
    const vendor_name = document.getElementById("vendor-name").value.trim();
    const gst_number = document.getElementById("vendor-gst").value.trim();
    const contact = document.getElementById("vendor-contact").value.trim();

    const isEdit = id !== "";
    const method = isEdit ? "PUT" : "POST";
    const url = isEdit ? `${API_BASE}/api/vendors/${id}` : `${API_BASE}/api/vendors`;

    try {
        const res = await fetch(url, {
            method: method,
            headers: getAuthHeaders(),
            body: JSON.stringify({ vendor_name, gst_number, contact })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Save vendor failed.");

        hideAddVendorModal();
        loadVendors();
    } catch (err) {
        alert(err.message);
    }
}

async function deleteVendorProfile(id) {
    if (!confirm("Deleting a vendor will delete all associated invoice files in the database. Are you sure you want to proceed?")) {
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/vendors/${id}`, {
            method: "DELETE",
            headers: getAuthHeaders()
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Delete vendor failed.");

        alert(data.message || "Successfully deleted vendor.");
        loadVendors();
        loadDashboardKPIs();
    } catch (e) {
        alert(e.message);
    }
}

// ========================================================
// 7. ANALYTICS & CHART.JS
// ========================================================
async function loadAnalytics() {
    try {
        const res = await fetch(`${API_BASE}/api/analytics`, { headers: getAuthHeaders() });
        const val = await res.json();

        // Bind KPI
        document.getElementById("analytics-processed-sum").textContent = val.kpis.total_expense;
        document.getElementById("analytics-accuracy").textContent = val.kpis.avg_accuracy;
        document.getElementById("analytics-growth").textContent = val.kpis.monthly_growth;

        const chartsData = val.charts;

        // Clear existing charts
        Object.keys(currentCharts).forEach(key => {
            currentCharts[key].destroy();
        });

        // --- Chart 1: Monthly Expenses (Bar) ---
        const ctx1 = document.getElementById("chart-monthly-expenses").getContext("2d");
        currentCharts.monthly = new Chart(ctx1, {
            type: "bar",
            data: {
                labels: chartsData.monthly_expenses.labels,
                datasets: [{
                    label: "Ledger Value (INR)",
                    data: chartsData.monthly_expenses.data,
                    backgroundColor: "#6366f1",
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: "#e2e8f0" } },
                    x: { grid: { display: false } }
                }
            }
        });

        // --- Chart 2: Vendor Spending (Pie) ---
        const ctx2 = document.getElementById("chart-vendor-spending").getContext("2d");
        currentCharts.vendor = new Chart(ctx2, {
            type: "pie",
            data: {
                labels: chartsData.vendor_spending.labels,
                datasets: [{
                    data: chartsData.vendor_spending.data,
                    backgroundColor: ["#0f172a", "#334155", "#475569", "#64748b", "#94a3b8", "#cbd5e1"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: "right", labels: { boxWidth: 12 } } }
            }
        });

        // --- Chart 3: Invoice Status (Doughnut) ---
        const ctx3 = document.getElementById("chart-invoice-status").getContext("2d");
        currentCharts.status = new Chart(ctx3, {
            type: "doughnut",
            data: {
                labels: chartsData.invoice_status.labels,
                datasets: [{
                    data: chartsData.invoice_status.data,
                    backgroundColor: ["#10b981", "#f59e0b", "#ef4444"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } } }
            }
        });

    } catch (e) {
        console.error(e);
    }
}

// ========================================================
// 8. AUDIT LOG LEDGER SYSTEM
// ========================================================
async function loadAuditLogs() {
    try {
        const res = await fetch(`${API_BASE}/api/logs`, { headers: getAuthHeaders() });
        const logs = await res.json();

        const terminal = document.getElementById("audit-logs-terminal");
        terminal.textContent = "";

        if (logs.length === 0) {
            terminal.textContent = "constructai_erp:~$ cat logs.txt\nNo system audit events recorded.";
            return;
        }

        let output = "constructai_erp:~$ tail -n 100 logs.txt\n";
        logs.forEach(log => {
            const time = new Date(log.timestamp).toLocaleString();
            output += `[${time}] [USER: ${log.user}] [ACTION: ${log.action}] -> ${log.details}\n`;
        });
        
        terminal.textContent = output;
        
        // Auto scroll to bottom
        terminal.scrollTop = terminal.scrollHeight;
    } catch (e) {
        console.error(e);
    }
}

// ========================================================
// 9. SYSTEM CONFIGS & SETTINGS
// ========================================================
async function loadSystemSettings() {
    try {
        const res = await fetch(`${API_BASE}/api/settings`, { headers: getAuthHeaders() });
        const data = await res.json();
        
        const healthModeText = document.getElementById("health-mode-text");
        if (healthModeText) {
            if (data.has_key) {
                healthModeText.textContent = "Active Gemini AI Core";
            } else {
                healthModeText.textContent = "Active Gemini AI Core (API Key Missing)";
            }
        }
        
        if (data.has_key) {
            document.getElementById("settings-api-key").placeholder = "••••••••••••••••••••••••••••••••";
        } else {
            document.getElementById("settings-api-key").placeholder = "Enter key starting with AIzaSy...";
        }

    } catch (e) {
        console.error(e);
    }
}

async function saveSystemSettings(e) {
    e.preventDefault();
    const apiKeyInput = document.getElementById("settings-api-key").value.trim();

    const payload = {};
    if (apiKeyInput) {
        payload.gemini_api_key = apiKeyInput;
    } else {
        alert("Please enter a Gemini API Key to save.");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/settings`, {
            method: "PUT",
            headers: getAuthHeaders(),
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Save configurations failed.");

        alert("System configurations saved successfully!");
        
        // Clear input field password trace
        document.getElementById("settings-api-key").value = "";
        
        loadSystemSettings();
    } catch (err) {
        alert(err.message);
    }
}

// --- Responsive Mobile Sidebar Controls ---
function toggleSidebarMenu() {
    const sidebar = document.querySelector(".sidebar");
    if (sidebar) {
        sidebar.classList.toggle("open");
    }
}
