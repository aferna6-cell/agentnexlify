import { faqData } from "./constants";

export default function Faq({
  openFaq,
  faqRefs,
  handleFaqToggle,
  getFaqMaxHeight,
}) {
  return (
    <section className="section lp-faq" id="faq">
      <div className="container">
        <div className="lp-faq-header">
          <div className="section-label reveal">FAQ</div>
          <h2 className="section-title reveal">Frequently Asked Questions</h2>
        </div>
        <div className="lp-faq-list reveal" role="list">
          {faqData.map((item) => (
            <div className="lp-faq-item" role="listitem" key={item.id}>
              <button
                className="lp-faq-question"
                aria-expanded={openFaq === item.id ? "true" : "false"}
                aria-controls={item.id}
                onClick={() => handleFaqToggle(item.id)}
              >
                {item.question}
                <svg
                  className="lp-faq-chevron"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
              <div
                className="lp-faq-answer"
                id={item.id}
                role="region"
                ref={(el) => {
                  faqRefs.current[item.id] = el;
                }}
                style={{ maxHeight: getFaqMaxHeight(item.id) }}
              >
                <div className="lp-faq-answer-inner">{item.answer}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
