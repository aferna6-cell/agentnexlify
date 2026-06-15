/**
 * Support contact API functions.
 */
import { request } from "./_client";

/**
 * Submit a support contact form.
 * @param {{ name: string, email: string, subject: string, message: string }} body
 * @param {string} token - Bearer auth token
 * @returns {Promise<{ sent: boolean }>}
 */
export function submitSupportContact(body, token) {
  return request("/api/v1/support/contact", {
    method: "POST",
    token,
    body,
  });
}
