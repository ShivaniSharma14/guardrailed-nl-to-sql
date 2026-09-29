// Your deployed backend. No trailing slash.
const API_BASE = "https://guardrailed-nl-to-sql.onrender.com";


// --------------------------------------------------
// Authentication state
// --------------------------------------------------

let accessToken = null;


// --------------------------------------------------
// Element references
// --------------------------------------------------

const emailInput = document.querySelector("#email-input");
const passwordInput = document.querySelector("#password-input");
const loginButton = document.querySelector("#login-button");
const loginError = document.querySelector("#login-error");

const loginView = document.querySelector("#login-view");
const registerView = document.querySelector("#register-view");
const appView = document.querySelector("#app-view");

const showRegisterLink = document.querySelector("#show-register-link");
const showLoginLink = document.querySelector("#show-login-link");

const registerEmailInput =
  document.querySelector("#register-email-input");

const registerPasswordInput =
  document.querySelector("#register-password-input");

const registerButton =
  document.querySelector("#register-button");

const registerError =
  document.querySelector("#register-error");

const logoutButton =
  document.querySelector("#logout-button");

const questionInput =
  document.querySelector("#question-input");

const askButton =
  document.querySelector("#ask-button");

const queryError =
  document.querySelector("#query-error");

const details =
  document.querySelector("#details");

const resultsTable =
  document.querySelector("#results-table");

const historyButton =
  document.querySelector("#history-button");

const historyTable =
  document.querySelector("#history-table");



  // --------------------------------------------------
// Token storage
// --------------------------------------------------

function saveTokens(access, refresh) {
  localStorage.setItem("access_token", access);
  if (refresh) localStorage.setItem("refresh_token", refresh);
}

function getAccessToken() {
  return localStorage.getItem("access_token");
}

function getRefreshToken() {
  return localStorage.getItem("refresh_token");
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  try {
    const response = await fetch(`${API_BASE}/api/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });

    if (!response.ok) {
      clearTokens(); // refresh token itself is dead or expired
      return null;
    }

    const data = await response.json();
    saveTokens(data.access, null); // no rotation configured, refresh token is unchanged
    return data.access;
  } catch (error) {
    return null;
  }
}

function showLoggedOutState() {
  clearTokens();
  appView.classList.add("hidden");
  registerView.classList.add("hidden");
  loginView.classList.remove("hidden");
}

// Wraps an authenticated request: retries once after a silent refresh on 401.
async function authedFetch(url, options = {}) {
  const token = getAccessToken();
  let response = await fetch(url, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${token}` },
  });

  if (response.status === 401) {
    const newToken = await refreshAccessToken();
    if (!newToken) {
      showLoggedOutState();
      loginError.textContent = "Your session expired. Please log in again.";
      throw new Error("Session expired");
    }
    response = await fetch(url, {
      ...options,
      headers: { ...options.headers, Authorization: `Bearer ${newToken}` },
    });
  }

  return response;
}


// --------------------------------------------------
// Login
// --------------------------------------------------

loginButton.addEventListener("click", async function () {

  const email = emailInput.value.trim();
  const password = passwordInput.value;

  loginError.textContent = "";

  if (!email || !password) {
    loginError.textContent =
      "Please enter email and password.";
    return;
  }

  setButtonLoading(loginButton, true, "Logging in...");

  try {

    const response = await fetch(
      `${API_BASE}/api/auth/login/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          email: email,
          password: password
        })
      }
    );

    const data = await response.json();

    if (!response.ok) {
      loginError.textContent =
        data.error || "Login failed.";
      return;
    }

    saveTokens(data.access, data.refresh);

    loginView.classList.add("hidden");
    registerView.classList.add("hidden");
    appView.classList.remove("hidden");

    questionInput.focus();


  } catch (error) {

    loginError.textContent =
      "Could not reach the server. Try again.";

  } finally {

    setButtonLoading(loginButton, false, "Log in");

  }
});


// --------------------------------------------------
// Registration
// --------------------------------------------------

showRegisterLink.addEventListener("click", function (event) {

  event.preventDefault();

  loginView.classList.add("hidden");
  registerView.classList.remove("hidden");

  registerEmailInput.focus();

});


showLoginLink.addEventListener("click", function (event) {

  event.preventDefault();

  registerView.classList.add("hidden");
  loginView.classList.remove("hidden");

  emailInput.focus();

});


registerButton.addEventListener("click", async function () {

  const email = registerEmailInput.value.trim();
  const password = registerPasswordInput.value;

  registerError.textContent = "";

  if (!email || !password) {
    registerError.textContent =
      "Please enter email and password.";
    return;
  }

  setButtonLoading(registerButton, true, "Registering...");

  try {

    const response = await fetch(
      `${API_BASE}/api/auth/register/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          email: email,
          password: password
        })
      }
    );

    const data = await response.json();

    if (!response.ok) {

      const firstError =
        Object.values(data)[0];

      registerError.textContent =
        Array.isArray(firstError)
          ? firstError[0]
          : "Registration failed.";

      return;
    }

    registerView.classList.add("hidden");
    loginView.classList.remove("hidden");

    emailInput.value = email;
    passwordInput.value = "";

    loginError.textContent =
      "Registration successful. Please log in.";

    emailInput.focus();

  } catch (error) {

    registerError.textContent =
      "Could not reach the server. Try again.";

  } finally {

    setButtonLoading(
      registerButton,
      false,
      "Register"
    );

  }

});


// --------------------------------------------------
// Logout
// --------------------------------------------------

logoutButton.addEventListener("click", function () {
  showLoggedOutState();

  questionInput.value = "";
  clearTable(resultsTable);
  clearTable(historyTable);
  queryError.textContent = "";

  emailInput.focus();
});


// --------------------------------------------------
// Ask a question
// --------------------------------------------------

askButton.addEventListener("click", async function () {

  const question = questionInput.value.trim();

  queryError.textContent = "";
  details.textContent = "";
  clearTable(resultsTable);

  if (!question) {
    queryError.textContent = "Please enter a question.";
    return;
  }

  setButtonLoading(askButton, true, "Running...");

  try {
    const response = await authedFetch(`${API_BASE}/api/query/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question }),
    });

    if (response.status === 429) {
      details.textContent =
        "You're asking too fast, or the demo has hit its daily capacity. Please wait a bit and try again.";
      return;
    }

    const data = await response.json();

    if (!response.ok) {
      queryError.textContent =
        `${data.error || "Request failed."}` +
        `${data.error_code ? ` (${data.error_code})` : ""}`;
      return;
    }

    renderTable(resultsTable, data.data, "No results returned.");

  } catch (error) {
    if (error.message !== "Session expired") {
      queryError.textContent = "Could not reach the server. Try again.";
    }
    // if it WAS a session expiry, authedFetch already switched to the login view
  } finally {
    setButtonLoading(askButton, false, "Ask");
  }

});


// --------------------------------------------------
// Load query history
// --------------------------------------------------

historyButton.addEventListener("click", async function () {

  clearTable(historyTable);
  setButtonLoading(historyButton, true, "Loading...");

  try {
    const response = await authedFetch(`${API_BASE}/api/queries/history/`);

    const data = await response.json();

    if (!response.ok) {
      renderMessageRow(historyTable, "Could not load history.");
      return;
    }

    renderTable(historyTable, data.results, "No query history yet.");

  } catch (error) {
    if (error.message !== "Session expired") {
      renderMessageRow(historyTable, "Could not reach the server.");
    }
  } finally {
    setButtonLoading(historyButton, false, "Load history");
  }

});
// --------------------------------------------------
// Generic table renderer
// --------------------------------------------------

function renderTable(table, rows, emptyMessage) {

  clearTable(table);

  if (!rows || rows.length === 0) {
    renderMessageRow(table, emptyMessage);
    return;
  }


  // Header
  const headerRow =
    document.createElement("tr");

  Object.keys(rows[0]).forEach(function (key) {

    const th =
      document.createElement("th");

    th.textContent = key;

    headerRow.appendChild(th);

  });

  table.appendChild(headerRow);


  // Data rows
  rows.forEach(function (row) {

    const tr =
      document.createElement("tr");


    Object.entries(row).forEach(function ([key, value]) {

      const td =
        document.createElement("td");


      // Status gets a visual badge.
      if (key === "status") {

        const status =
          document.createElement("span");

        status.textContent = value;

        status.classList.add(
          "status",
          `status-${String(value).toLowerCase()}`
        );

        td.appendChild(status);

      } else {

        td.textContent =
          value ?? "";

      }


      tr.appendChild(td);

    });


    table.appendChild(tr);

  });

}


// --------------------------------------------------
// Table helpers
// --------------------------------------------------

function clearTable(table) {
  table.innerHTML = "";
}


function renderMessageRow(table, message) {

  const row =
    document.createElement("tr");

  const cell =
    document.createElement("td");

  cell.textContent = message;

  cell.colSpan = 20;

  row.appendChild(cell);

  table.appendChild(row);

}


// --------------------------------------------------
// Button loading state
// --------------------------------------------------

function setButtonLoading(button, loading, text) {

  button.disabled = loading;
  button.textContent = text;

}


window.addEventListener('pageshow', (event) => {
    // If the page was restored from the back-forward cache, force a fresh reload
    if (event.persisted) {
        window.location.reload();
    }
});


(async function initSession() {
  if (!getAccessToken()) return; // never logged in, show login screen as-is

  const refreshed = await refreshAccessToken();
  if (refreshed) {
    loginView.classList.add("hidden");
    registerView.classList.add("hidden");
    appView.classList.remove("hidden");
  } else {
    showLoggedOutState();
  }
})();