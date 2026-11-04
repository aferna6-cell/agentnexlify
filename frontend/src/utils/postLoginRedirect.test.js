import { describe, expect, it } from "vitest";
import {
  DASHBOARD_PATH,
  isLoginPath,
  replaceLoginWithDashboard,
} from "./postLoginRedirect";

describe("post-login redirect", () => {
  it("replaces /login with /dashboard", () => {
    const history = {
      replaceState: (state, title, url) => (history.url = url),
      url: "/login",
    };
    expect(replaceLoginWithDashboard(history, "/login")).toBe(true);
    expect(history.url).toBe(DASHBOARD_PATH);
  });

  it("replaces /login/ with the same dashboard path", () => {
    const history = {
      replaceState: (_s, _t, url) => {
        history.url = url;
      },
      url: "",
    };
    expect(replaceLoginWithDashboard(history, "/login/")).toBe(true);
    expect(history.url).toBe("/dashboard");
  });

  it("does not rewrite an already-dashboard url", () => {
    const history = {
      replaceState: () => {
        throw new Error("should not replace");
      },
    };
    expect(replaceLoginWithDashboard(history, "/dashboard")).toBe(false);
  });

  it("does not treat login as a prefix of another route", () => {
    expect(isLoginPath("/login-help")).toBe(false);
    expect(isLoginPath("/client/login/acme")).toBe(false);
  });

  it("treats the bare login path as the auth screen", () => {
    expect(isLoginPath("/login")).toBe(true);
  });
});
