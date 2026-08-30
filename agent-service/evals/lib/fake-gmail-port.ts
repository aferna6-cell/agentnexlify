/**
 * In-process Gmail double. delivered is always false. No network.
 */

export interface FakeGmailSendInput {
  to: string;
  subject?: string;
  body?: string;
  rfc822MsgId?: string;
}

export interface FakeGmailSendRecord extends FakeGmailSendInput {
  messageId: string;
  at: string;
}

export interface GmailPort {
  readonly name: string;
  readonly durable: boolean;
  send(
    input: FakeGmailSendInput,
  ): Promise<{ messageId: string; delivered: false }>;
  findByRfc822MsgId(msgid: string): string | null;
}

export class FakeGmailPort implements GmailPort {
  readonly name = "fake_gmail";
  readonly durable = false;
  readonly sent: FakeGmailSendRecord[] = [];

  async send(
    input: FakeGmailSendInput,
  ): Promise<{ messageId: string; delivered: false }> {
    if (input.rfc822MsgId) {
      const existing = this.findByRfc822MsgId(input.rfc822MsgId);
      if (existing) return { messageId: existing, delivered: false };
    }
    const messageId = `fake_gmail_${this.sent.length + 1}`;
    this.sent.push({ ...input, messageId, at: new Date().toISOString() });
    return { messageId, delivered: false };
  }

  findByRfc822MsgId(msgid: string): string | null {
    return this.sent.find((s) => s.rfc822MsgId === msgid)?.messageId ?? null;
  }
}
