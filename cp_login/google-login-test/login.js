async function handleCredentialResponse(response) {
  console.log("Google token received:", response.credential);
  const token = response.credential;

  try {
    const res = await fetch("http://localhost:8000/auth/google/signup/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ token }),
    });

    // Check if response content-type is JSON before parsing
    const contentType = res.headers.get("content-type");
    let data;
    if (contentType && contentType.includes("application/json")) {
      data = await res.json();
    } else {
      const text = await res.text();
      console.error("Expected JSON, got:", text);
      throw new Error("Unexpected response format");
    }

    if (res.ok) {
      alert(data.message || "Login successful!");

      console.log("Email:", data.email);
      console.log("Access Token:", data.access);
      console.log("Refresh Token:", data.refresh);

      // Store tokens safely (consider security implications)
      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);
      localStorage.setItem("email", data.email);

      // Redirect to dashboard or another page if needed
      // window.location.href = "/dashboard.html";
    } else {
      alert(data.detail || "Login failed.");
    }
  } catch (err) {
    console.error("Login error:", err);
    alert("Something went wrong while logging in.");
  }
}
window.handleCredentialResponse = handleCredentialResponse;
