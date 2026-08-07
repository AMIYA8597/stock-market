const baseUrl = "http://127.0.0.1:8000/api/v1";

async function run() {
  console.log("Registering user...");
  try {
    const regRes = await fetch(`${baseUrl}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "test@example.com", password: "Password123!", full_name: "Test User" }),
    });
    console.log("Register status:", regRes.status);
    console.log(await regRes.text());
  } catch (e) {
    console.error(e);
  }

  console.log("\nLogging in...");
  let token = "";
  try {
    const loginRes = await fetch(`${baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "test@example.com", password: "Password123!" }),
    });
    console.log("Login status:", loginRes.status);
    const loginData = await loginRes.json();
    console.log(loginData);
    token = loginData.access_token;
  } catch (e) {
    console.error(e);
  }

  if (token) {
    console.log("\nFetching profile...");
    try {
      const meRes = await fetch(`${baseUrl}/auth/me`, {
        method: "GET",
        headers: { "Authorization": `Bearer ${token}` },
      });
      console.log("Me status:", meRes.status);
      console.log(await meRes.text());
    } catch (e) {
      console.error(e);
    }
  }
}

run();
