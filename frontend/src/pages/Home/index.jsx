import { useState, useEffect, useCallback, useRef } from "react";
import "../../styles/home.css";
import { getUserEmail } from "./utils";
import StructuredData from "./StructuredData";
import Nav from "./Nav";
import Hero from "./Hero";
import HowItWorks from "./HowItWorks";
import Features from "./Features";
import Pricing from "./Pricing";
import FinalCta from "./FinalCta";
import DemoPreview from "./DemoPreview";
import Faq from "./Faq";
import Footer from "./Footer";
import FloatingCta from "./FloatingCta";

export default function Home() {
  const [navScrolled, setNavScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState(null);
  const [showFloatingCta, setShowFloatingCta] = useState(false);
  const [floatingCtaDismissed, setFloatingCtaDismissed] = useState(
    () => sessionStorage.getItem("anx_cta_dismissed") === "1",
  );
  const faqRefs = useRef({});
  const isLoggedIn = getUserEmail() !== null;

  useEffect(() => {
    const handleScroll = () => setNavScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  useEffect(() => {
    const reveals = document.querySelectorAll(".landing-page .reveal");
    if (!("IntersectionObserver" in window)) {
      reveals.forEach((el) => el.classList.add("visible"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
    );
    reveals.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (floatingCtaDismissed) return;
    const showTimer = setTimeout(() => setShowFloatingCta(true), 3000);
    const handleScroll = () => {
      const pricing = document.getElementById("pricing");
      if (pricing) {
        const rect = pricing.getBoundingClientRect();
        if (rect.top < window.innerHeight && rect.bottom > 0) {
          setShowFloatingCta(false);
        } else if (!floatingCtaDismissed) {
          setShowFloatingCta(true);
        }
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      clearTimeout(showTimer);
      window.removeEventListener("scroll", handleScroll);
    };
  }, [floatingCtaDismissed]);

  const toggleMenu = useCallback(() => setMenuOpen((p) => !p), []);
  const closeMenu = useCallback(() => setMenuOpen(false), []);
  const dismissFloatingCta = useCallback(() => {
    setShowFloatingCta(false);
    setFloatingCtaDismissed(true);
    sessionStorage.setItem("anx_cta_dismissed", "1");
  }, []);
  const handleFaqToggle = useCallback(
    (id) => setOpenFaq((p) => (p === id ? null : id)),
    [],
  );
  const getFaqMaxHeight = useCallback(
    (id) => {
      if (openFaq === id && faqRefs.current[id]) {
        return faqRefs.current[id].scrollHeight + "px";
      }
      return "0";
    },
    [openFaq],
  );

  return (
    <div className="landing-page">
      <StructuredData />
      <Nav
        navScrolled={navScrolled}
        menuOpen={menuOpen}
        isLoggedIn={isLoggedIn}
        toggleMenu={toggleMenu}
        closeMenu={closeMenu}
      />
      <Hero />
      <HowItWorks />
      <Features />
      <Pricing />
      <FinalCta />
      <DemoPreview />
      <Faq
        openFaq={openFaq}
        faqRefs={faqRefs}
        handleFaqToggle={handleFaqToggle}
        getFaqMaxHeight={getFaqMaxHeight}
      />
      <Footer />
      <FloatingCta
        visible={showFloatingCta && !floatingCtaDismissed}
        onDismiss={dismissFloatingCta}
      />
    </div>
  );
}
