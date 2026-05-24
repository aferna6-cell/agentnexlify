import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { demoTabs } from "./constants";
import DemoSlide from "./DemoSlide";

export default function DemoPreview() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const iv = setInterval(
      () => setActive((p) => (p + 1) % demoTabs.length),
      5000,
    );
    return () => clearInterval(iv);
  }, []);

  return (
    <section className="section lp-demo-preview" id="demo">
      <div className="container">
        <div className="demo-preview-wrap">
          <div className="demo-browser">
            <div className="demo-browser-bar">
              <span className="demo-dot" />
              <span className="demo-dot" />
              <span className="demo-dot" />
              <span className="demo-url">
                app.agentnexlify.com/
                {demoTabs[active].toLowerCase().replace(/ /g, "-")}
              </span>
            </div>
            <div className="demo-screen">
              <div className="demo-sidebar">
                <div className="demo-sidebar-logo">NexLiFy</div>
                {demoTabs.map((t, i) => (
                  <button
                    key={t}
                    className={`demo-sidebar-item${i === active ? " active" : ""}`}
                    onClick={() => setActive(i)}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <div className="demo-main">
                <div className="ds-slide-wrap">
                  {demoTabs.map((t, i) => (
                    <div
                      key={t}
                      className={`ds-slide${i === active ? " ds-slide-active" : ""}`}
                    >
                      <DemoSlide tab={t} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="demo-indicators">
            {demoTabs.map((t, i) => (
              <button
                key={t}
                className={`demo-ind${i === active ? " active" : ""}`}
                onClick={() => setActive(i)}
                aria-label={t}
              />
            ))}
          </div>
        </div>
        <div className="demo-preview-cta reveal">
          <div className="section-label">Demo</div>
          <h2 className="section-title">Try Our Demo</h2>
          <Link to="/demo" className="btn-primary">
            Book a Demo {"→"}
          </Link>
        </div>
      </div>
    </section>
  );
}
