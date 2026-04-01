// frontend/src/pages/wizard/WizardStepServices.jsx
import { useState } from "react";

// Industry-specific service suggestions
const SUGGESTIONS = {
  plumbing: ["Drain Cleaning", "Water Heater Installation", "Leak Repair", "Pipe Replacement", "Sewer Line Repair"],
  hvac: ["AC Repair", "Furnace Installation", "Duct Cleaning", "Thermostat Installation", "System Tune-up"],
  auto_shop: ["Oil Change", "Tire Rotation", "Brake Service", "Engine Diagnostics", "Transmission Repair"],
  salon: ["Haircut", "Color & Highlights", "Blowout", "Keratin Treatment", "Extensions"],
  dental: ["Teeth Cleaning", "Teeth Whitening", "Dental Implants", "Invisalign", "Emergency Care"],
  restaurant: ["Dine In", "Takeout", "Delivery", "Catering", "Private Events"],
  default: ["Consultation", "Custom Quote", "Emergency Service", "Maintenance", "Installation"],
};

export default function WizardStepServices({ wizardData, onNext, onBack }) {
  const [services, setServices] = useState(wizardData.services || []);
  const [serviceInput, setServiceInput] = useState("");
  const [faqs, setFaqs] = useState(
    wizardData.faqs?.length ? wizardData.faqs : [{ question: "", answer: "" }]
  );

  const suggestions = SUGGESTIONS[wizardData.business_type] || SUGGESTIONS.default;

  function addService(name) {
    const trimmed = name.trim();
    if (!trimmed || services.includes(trimmed) || services.length >= 10) return;
    setServices(s => [...s, trimmed]);
    setServiceInput("");
  }

  function removeService(name) {
    setServices(s => s.filter(x => x !== name));
  }

  function addFaq() {
    if (faqs.length >= 8) return;
    setFaqs(f => [...f, { question: "", answer: "" }]);
  }

  function removeFaq(i) {
    setFaqs(f => f.filter((_, idx) => idx !== i));
  }

  function updateFaq(i, field, value) {
    setFaqs(f => f.map((faq, idx) => idx === i ? { ...faq, [field]: value } : faq));
  }

  function handleNext() {
    const validFaqs = faqs.filter(f => f.question.trim() && f.answer.trim());
    onNext({ services, faqs: validFaqs });
  }

  return (
    <div>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>Services & FAQs</h2>
      <p style={{ color: "rgba(255,255,255,0.5)", marginBottom: 32, fontSize: "0.9rem" }}>
        Tell your AI assistant what you offer and how to answer common questions.
      </p>

      {/* Services */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontWeight: 600, marginBottom: 12 }}>What services do you offer?</div>

        {/* Chips */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
          {services.map(s => (
            <div key={s} style={chipStyle}>
              {s}
              <button onClick={() => removeService(s)} style={chipXStyle}>&times;</button>
            </div>
          ))}
        </div>

        {/* Add service input */}
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={serviceInput}
            onChange={e => setServiceInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addService(serviceInput))}
            placeholder="Type a service and press Enter"
            style={inputStyle}
          />
          <button onClick={() => addService(serviceInput)} style={{ ...btnSmall, flexShrink: 0 }}>Add</button>
        </div>

        {/* Suggestions */}
        <div style={{ marginTop: 10 }}>
          <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.4)", marginRight: 8 }}>Suggestions:</span>
          {suggestions.filter(s => !services.includes(s)).slice(0, 5).map(s => (
            <button key={s} onClick={() => addService(s)} style={suggStyle}>{s}</button>
          ))}
        </div>
      </div>

      {/* FAQs */}
      <div>
        <div style={{ fontWeight: 600, marginBottom: 12 }}>Common customer questions <span style={{ color: "rgba(255,255,255,0.4)", fontWeight: 400, fontSize: "0.85rem" }}>(optional)</span></div>
        {faqs.map((faq, i) => (
          <div key={i} style={{ background: "rgba(255,255,255,0.04)", borderRadius: 10, padding: 16, marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.4)" }}>Q&A #{i + 1}</span>
              {faqs.length > 1 && (
                <button onClick={() => removeFaq(i)} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: "0.85rem" }}>Remove</button>
              )}
            </div>
            <input
              placeholder="Customer question (e.g. Do you offer emergency service?)"
              value={faq.question}
              onChange={e => updateFaq(i, "question", e.target.value)}
              style={{ ...inputStyle, marginBottom: 8 }}
              maxLength={500}
            />
            <textarea
              placeholder="Your answer"
              value={faq.answer}
              onChange={e => updateFaq(i, "answer", e.target.value)}
              rows={2}
              style={{ ...inputStyle, resize: "vertical" }}
              maxLength={2000}
            />
          </div>
        ))}
        {faqs.length < 8 && (
          <button onClick={addFaq} style={{ ...btnSmall, width: "100%", marginBottom: 8 }}>+ Add Question</button>
        )}
      </div>

      <div style={{ display: "flex", gap: 12, marginTop: 32 }}>
        <button onClick={onBack} style={{ ...btnStyle, background: "rgba(255,255,255,0.08)", flex: 1 }}>← Back</button>
        <button onClick={handleNext} style={{ ...btnStyle, flex: 2 }}>Continue →</button>
      </div>
    </div>
  );
}

const inputStyle = { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "10px 14px", color: "#e2e8f0", fontSize: "0.9rem", width: "100%", boxSizing: "border-box" };
const chipStyle = { display: "flex", alignItems: "center", gap: 6, background: "rgba(99,102,241,0.2)", border: "1px solid rgba(99,102,241,0.4)", borderRadius: 20, padding: "4px 12px", fontSize: "0.85rem", color: "#a5b4fc" };
const chipXStyle = { background: "none", border: "none", cursor: "pointer", color: "#a5b4fc", fontSize: "1rem", lineHeight: 1, padding: 0 };
const btnStyle = { padding: "14px", background: "#6366f1", color: "#fff", border: "none", borderRadius: 10, fontSize: "1rem", fontWeight: 600, cursor: "pointer" };
const btnSmall = { padding: "8px 16px", background: "rgba(99,102,241,0.2)", color: "#a5b4fc", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 8, fontSize: "0.85rem", cursor: "pointer" };
const suggStyle = { marginRight: 6, marginBottom: 4, padding: "4px 10px", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 16, fontSize: "0.8rem", color: "rgba(255,255,255,0.6)", cursor: "pointer" };
