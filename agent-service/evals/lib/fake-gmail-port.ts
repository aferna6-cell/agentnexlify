/**
 * Eval-only Gmail boundary.
 *
 * The only send port this measurement may install. It records attempts in
 * memory and reports `delivered: false`. It is not a live client and it is
 * not the production mailbox port.
 */

import type { GmailPort } from "../../src/agent-os/actions/ports.ts";

export interface FakeGmailSendInput {
  to: string;
  subject?: string;
  body?: string;
}

export interface FakeGmailSendRecord extends FakeGmailSendInput {
  at: string;
}

export class FakeGmailPort implements GmailPort {
  readonly name = "fake_gmail";
  readonly durable = false;
  readonly sent: FakeGmailSendRecord[] = [];

  async send(
    input: FakeGmailSendInput,
  ): Promise<{ messageId: string; delivered: false }> {
    this.sent.push({ ...input, at: new Date().toISOString() });
    return { messageId: `fake_gmail_${this.sent.length}`, delivered: false };
  }
}
