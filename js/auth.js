const API_BASE = "https://survey-site-98jc.onrender.com";

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const username = e.target.username.value;
  const password = e.target.password.value;

  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const data = await res.json();
  if (res.ok) {
    localStorage.setItem("token", data.token);
    window.location.href = "dashboard.html";
  } else {
    document.getElementById("error").textContent = data.error || "Login failed";
  }
});
