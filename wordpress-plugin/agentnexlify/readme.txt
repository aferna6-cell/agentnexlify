=== AgentNexLiFy Chat Widget ===
Contributors: agentnexlify
Tags: chat, ai, chatbot, lead capture, customer support
Requires at least: 5.8
Tested up to: 6.5
Requires PHP: 7.2
Stable tag: 1.0.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

One-click install for the AgentNexLiFy AI chat widget. Paste your widget key, save, and the assistant goes live — no theme editing, no code.

== Description ==

AgentNexLiFy puts an AI assistant on your website that answers questions, captures leads, and books appointments for your business 24/7.

This plugin installs that assistant on WordPress without touching your theme. You paste the widget key from your AgentNexLiFy dashboard, hit save, and the chat widget appears on every page of your site.

* No code, no `<script>` tag to place by hand
* No theme file editing
* Works with any theme that uses the standard `wp_footer` hook (nearly all do)
* Turn the widget on or off with one checkbox

You need an AgentNexLiFy account to get a widget key. Sign up at https://agentnexlify.com.

== Installation ==

1. Install and activate the plugin.
2. Go to **Settings → AgentNexLiFy**.
3. Paste your **Widget key** (starts with `wk_`) from your AgentNexLiFy dashboard.
4. Leave **Show widget** checked and click **Save Changes**.
5. Visit your site — the chat bubble appears in the corner.

Where to find your widget key: in the AgentNexLiFy dashboard, open the onboarding "Your embed code" step, or Widget settings. It is the value of `data-api-key` in the embed snippet.

== Frequently Asked Questions ==

= Is my widget key a secret? =

No. The widget key is public by design — it is meant to be published on your website, exactly like the `<script>` snippet you would otherwise paste by hand. It does not grant access to your AgentNexLiFy account.

= Will this slow down my site? =

The widget loads asynchronously, so it does not block your page from rendering.

= The widget is not showing up. =

Check that **Show widget** is checked and a valid widget key starting with `wk_` is saved. Some heavily-customized themes or aggressive caching/optimization plugins can strip footer scripts — clear your cache after saving.

== Changelog ==

= 1.0.0 =
* Initial release. Settings page, one-click widget injection via `wp_footer`, optional brand color and advanced loader overrides.
