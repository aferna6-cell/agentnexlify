export function getUserEmail() {
  try {
    const token = localStorage.getItem("anx_token");
    if (!token) return null;
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (payload.exp && payload.exp * 1000 < Date.now()) return null;
    return payload.email || null;
  } catch {
    return null;
  }
}
