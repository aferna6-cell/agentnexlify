/**
 * useIsMobile - returns true when viewport width is at or below 768px.
 * Safe in environments without matchMedia (SSR, jsdom): resolves false.
 */
import { useState, useEffect } from "react";

const QUERY = "(max-width: 768px)";

function canMatch() {
  return typeof window !== "undefined" && typeof window.matchMedia === "function";
}

export default function useIsMobile() {
  const [isMobile, setIsMobile] = useState(() => {
    if (!canMatch()) return false;
    return window.matchMedia(QUERY).matches;
  });

  useEffect(() => {
    if (!canMatch()) return;
    const mql = window.matchMedia(QUERY);
    const handler = (e) => setIsMobile(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return isMobile;
}
