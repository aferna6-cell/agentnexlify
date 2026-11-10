import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const authState = { user: { tenantId: "ten-1", role: "owner" }, token: "tok" };
vi.mock("../context/AuthContext", () => ({ useAuth: () => authState }));

const inboxRows = [
  { session_id: "s-real", lead_name: "Chris", preview: "My alerts stopped", message_count: 2, tags: [] },
  { session_id: "s-junk", lead_name: "Spammer", preview: "Buy followers", message_count: 1, tags: [] },
];
const spamRows = [
  { session_id: "s-old", lead_name: "Old spam", preview: "crypto", message_count: 1, tags: ["spam"], is_spam: true },
];

vi.mock("../utils/api/conversations", () => ({
  fetchConversations: vi.fn(async (_t, _k, { view } = {}) =>
    view === "spam"
      ? { conversations: spamRows, spam_count: 1 }
      : { conversations: inboxRows, spam_count: 1 },
  ),
  fetchConversationMessages: vi.fn().mockResolvedValue({ messages: [] }),
  updateConversationTags: vi.fn(),
}));
vi.mock("../utils/api/inbox", () => ({
  assignConversation: vi.fn(),
  fetchConversationNotes: vi.fn().mockResolvedValue({ notes: [] }),
  createConversationNote: vi.fn(),
  deleteConversationNote: vi.fn(),
  replyToConversation: vi.fn(),
  setConversationsSpam: vi.fn(async (_t, _k, ids, spam) => ({ spam, updated: ids, not_found: [] })),
}));
vi.mock("../utils/api/team", () => ({ fetchTeamMembers: vi.fn().mockResolvedValue({ members: [] }) }));
vi.mock("../utils/api/tags", () => ({ fetchTagDefinitions: vi.fn().mockResolvedValue({ tags: [] }) }));
vi.mock("../utils/api/crm", () => ({ addClientNote: vi.fn() }));
vi.mock("../utils/api/snippets", () => ({ fetchSnippets: vi.fn().mockResolvedValue([]) }));
vi.mock("../utils/api/misc", () => ({ sendSms: vi.fn() }));
vi.mock("./Dashboard/QuickActions", () => ({ QuickAddLeadModal: () => null }));

import ConversationsPage from "./ConversationsPage";
import { setConversationsSpam } from "../utils/api/inbox";
import { fetchConversations } from "../utils/api/conversations";

describe("Conversations spam", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.user = { tenantId: "ten-1", role: "owner" };
  });

  it("bulk marks selected conversations as spam, hides them, and offers undo", async () => {
    render(<ConversationsPage />);
    fireEvent.click(await screen.findByLabelText("Select conversation with Spammer"));
    fireEvent.click(screen.getByRole("button", { name: "Mark as spam" }));

    await waitFor(() =>
      expect(setConversationsSpam).toHaveBeenCalledWith("ten-1", "tok", ["s-junk"], true),
    );
    await waitFor(() => expect(screen.queryByText("Spammer")).toBeNull());
    expect(screen.getByText("Chris")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Spam (2)" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() =>
      expect(setConversationsSpam).toHaveBeenLastCalledWith("ten-1", "tok", ["s-junk"], false),
    );
  });

  it("lists spam in the Spam view and restores it", async () => {
    render(<ConversationsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Spam (1)" }));
    expect(await screen.findByText("Old spam")).toBeTruthy();
    expect(fetchConversations).toHaveBeenLastCalledWith("ten-1", "tok", expect.objectContaining({ view: "spam" }));

    fireEvent.click(screen.getByText("Old spam"));
    fireEvent.click(await screen.findByRole("button", { name: "Restore" }));
    await waitFor(() =>
      expect(setConversationsSpam).toHaveBeenCalledWith("ten-1", "tok", ["s-old"], false),
    );
    await waitFor(() => expect(screen.queryByText("Old spam")).toBeNull());
  });

  it("gives plain team members no spam controls", async () => {
    authState.user = { tenantId: "ten-1", role: "member" };
    render(<ConversationsPage />);
    expect(await screen.findByText("Chris")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Spam \(/ })).toBeNull();
    expect(screen.queryByLabelText("Select conversation with Chris")).toBeNull();
  });
});
