/** Path the app shows after a successful owner login. */
export const DASHBOARD_PATH = "/dashboard";

export function isLoginPath(pathname) {
  return pathname === "/login" || pathname.startsWith("/login/");
}

/**
 * Replace /login with /dashboard so the address bar and back stack match
 * the signed-in app. Returns true when a replacement was made.
 */
export function replaceLoginWithDashboard(history, pathname) {
  if (!isLoginPath(pathname)) return false;
  history.replaceState(null, "", DASHBOARD_PATH);
  return true;
}
