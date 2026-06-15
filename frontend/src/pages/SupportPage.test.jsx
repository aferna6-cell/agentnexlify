import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// --- Mock auth context ---
let mockAuth;
vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

// --- Mock the support API module ---
vi.mock("../utils/api/support", () => ({
  submitSupportContact: vi.fn(),
}));

import { submitSupportContact } from "../utils/api/support";
import SupportPage from "./SupportPage";

beforeEach(() => {
  mockAuth = {
    user: { name: "Ada Lovelace", email: "ada@example.com" },
    token: "test-jwt",
  };
  submitSupportContact.mockReset();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fillValidForm() {
  // Subject is the only field that needs explicit filling; name and email are
  // pre-filled from auth context.
  fireEvent.change(screen.getByLabelText(/subject/i), {
    target: { value: "Bug report" },
  });
  fireEvent.change(screen.getByLabelText(/message/i), {
    target: { value: "The widget stops responding after 5 minutes." },
  });
}

// ---------------------------------------------------------------------------
// Suite: Rendering
// ---------------------------------------------------------------------------

describe("SupportPage - rendering", () => {
  it("renders all four form fields", () => {
    render(<SupportPage />);

    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/subject/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/message/i)).toBeInTheDocument();
  });

  it("pre-fills name and email from auth context", () => {
    render(<SupportPage />);

    expect(screen.getByLabelText(/name/i)).toHaveValue("Ada Lovelace");
    expect(screen.getByLabelText(/email/i)).toHaveValue("ada@example.com");
  });

  it("renders the submit button in its idle state", () => {
    render(<SupportPage />);

    const btn = screen.getByTestId("submit-btn");
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent("Send Message");
    expect(btn).not.toBeDisabled();
  });

  it("pre-fills name from businessName when name is absent", () => {
    mockAuth = {
      user: { businessName: "Acme Corp", email: "info@acme.com" },
      token: "test-jwt",
    };
    render(<SupportPage />);

    expect(screen.getByLabelText(/name/i)).toHaveValue("Acme Corp");
  });
});

// ---------------------------------------------------------------------------
// Suite: Validation
// ---------------------------------------------------------------------------

describe("SupportPage - client-side validation", () => {
  it("shows required-field errors when form is submitted empty after clearing pre-fills", async () => {
    render(<SupportPage />);

    // Clear pre-filled fields so they are blank
    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "" } });

    fireEvent.submit(screen.getByRole("button", { name: /send message/i }).closest("form"));

    expect(await screen.findByTestId("error-name")).toBeInTheDocument();
    expect(screen.getByTestId("error-email")).toBeInTheDocument();
    expect(screen.getByTestId("error-subject")).toBeInTheDocument();
    expect(screen.getByTestId("error-message")).toBeInTheDocument();
    expect(submitSupportContact).not.toHaveBeenCalled();
  });

  it("blocks submit and shows email error when email is invalid", async () => {
    render(<SupportPage />);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "not-an-email" },
    });
    fireEvent.change(screen.getByLabelText(/subject/i), {
      target: { value: "General question" },
    });
    fireEvent.change(screen.getByLabelText(/message/i), {
      target: { value: "Hello" },
    });

    fireEvent.submit(screen.getByTestId("submit-btn").closest("form"));

    expect(await screen.findByTestId("error-email")).toBeInTheDocument();
    expect(screen.getByTestId("error-email")).toHaveTextContent(/valid email/i);
    expect(submitSupportContact).not.toHaveBeenCalled();
  });

  it("clears a field error when the user corrects that field", async () => {
    render(<SupportPage />);

    // Trigger validation error
    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: "" } });
    fireEvent.submit(screen.getByTestId("submit-btn").closest("form"));
    expect(await screen.findByTestId("error-name")).toBeInTheDocument();

    // Correct the field - error should clear
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "Fixed Name" },
    });
    expect(screen.queryByTestId("error-name")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Suite: Successful submission
// ---------------------------------------------------------------------------

describe("SupportPage - successful submission", () => {
  it("calls submitSupportContact with the correct payload and shows success state", async () => {
    submitSupportContact.mockResolvedValueOnce({ sent: true });

    render(<SupportPage />);
    fillValidForm();

    fireEvent.submit(screen.getByTestId("submit-btn").closest("form"));

    // Button shows loading state
    expect(screen.getByTestId("submit-btn")).toHaveTextContent("Sending...");
    expect(screen.getByTestId("submit-btn")).toBeDisabled();

    // Success state appears
    expect(await screen.findByTestId("success-state")).toBeInTheDocument();
    expect(screen.getByTestId("success-state")).toHaveTextContent(
      /thanks.*get back to you/i,
    );

    // API was called once with expected shape
    expect(submitSupportContact).toHaveBeenCalledTimes(1);
    expect(submitSupportContact).toHaveBeenCalledWith(
      {
        name: "Ada Lovelace",
        email: "ada@example.com",
        subject: "Bug report",
        message: "The widget stops responding after 5 minutes.",
      },
      "test-jwt",
    );
  });

  it("resets the form when 'Send Another Message' is clicked after success", async () => {
    submitSupportContact.mockResolvedValueOnce({ sent: true });

    render(<SupportPage />);
    fillValidForm();
    fireEvent.submit(screen.getByTestId("submit-btn").closest("form"));

    await screen.findByTestId("success-state");

    fireEvent.click(screen.getByRole("button", { name: /send another/i }));

    // Form is visible again, subject and message cleared, name/email retained
    expect(screen.getByTestId("submit-btn")).toBeInTheDocument();
    expect(screen.getByLabelText(/name/i)).toHaveValue("Ada Lovelace");
    expect(screen.getByLabelText(/subject/i)).toHaveValue("");
    expect(screen.getByLabelText(/message/i)).toHaveValue("");
  });
});

// ---------------------------------------------------------------------------
// Suite: Failed submission
// ---------------------------------------------------------------------------

describe("SupportPage - failed submission", () => {
  it("shows the submit error message when the API returns a 500", async () => {
    submitSupportContact.mockRejectedValueOnce({
      status: 500,
      body: { detail: "Email service unavailable." },
      message: "Email service unavailable.",
    });

    render(<SupportPage />);
    fillValidForm();
    fireEvent.submit(screen.getByTestId("submit-btn").closest("form"));

    const errEl = await screen.findByTestId("submit-error");
    expect(errEl).toBeInTheDocument();
    expect(errEl).toHaveTextContent(/email service unavailable/i);

    // Form stays visible for retry
    expect(screen.getByTestId("submit-btn")).toBeInTheDocument();
    expect(screen.getByTestId("submit-btn")).toHaveTextContent("Send Message");
    expect(screen.getByTestId("submit-btn")).not.toBeDisabled();
  });

  it("shows a generic error message when the API rejects with no detail", async () => {
    submitSupportContact.mockRejectedValueOnce(new Error("Network error"));

    render(<SupportPage />);
    fillValidForm();
    fireEvent.submit(screen.getByTestId("submit-btn").closest("form"));

    const errEl = await screen.findByTestId("submit-error");
    expect(errEl).toBeInTheDocument();
    expect(errEl).toHaveTextContent(/network error/i);
  });
});
