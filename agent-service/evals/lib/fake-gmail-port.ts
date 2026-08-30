/**
 * Eval-only Gmail boundary.
 *
 * The unsafe-action runner is proposal-level: it may record that the engine
 * *wanted* to send, but it must never touch live Gmail or production send.
 * This port stores attempts in memory and reports `delivered: false`.
 */

export interface FakeGmailSendInput {
  to: string;
  subject?: string;
  body?: string;
}

export interface FakeGmailSendRecord extends FakeGmailSendInput {
  at: string;
}

export class FakeGmailPort {
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
