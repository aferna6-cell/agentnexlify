# AgentNexLiFy WordPress Plugin

One-click install of the AgentNexLiFy AI chat widget for WordPress sites. Solves the #1 self-onboarding blocker: non-technical owners on WordPress (~40% of SMB sites) can't paste a `<script>` tag before `</body>`. This plugin does it for them.

## What it does

- Adds a **Settings → AgentNexLiFy** admin page.
- Owner pastes their public widget key (`wk_...`) and saves.
- The plugin injects the **byte-identical loader snippet** (the same `<script ... data-api-key="..." async>` shown in the dashboard embed step) into `wp_footer`, just before `</body>`.
- No theme editing, no FTP, no code.

The widget JavaScript itself is **not** bundled here — the plugin only emits the loader `<script>` tag pointing at the hosted loader (`app.agentnexlify.com/widget/agentnexlify-widget.js`). This keeps the widget byte-identical with `widget/agentnexlify-widget.js` and `frontend/public/widget/agentnexlify-widget.js` (CLAUDE.md invariant #4) — there is no third copy to drift.

## Layout

```
wordpress-plugin/
  agentnexlify/
    agentnexlify.php   # main plugin: settings page + wp_footer injection
    readme.txt         # WordPress.org-format readme (shown in plugin directory)
    uninstall.php      # removes the single wp_option on delete
  README.md            # this file (developer/packaging notes)
```

## Security notes

- The widget key (`wk_...`) is a **public** per-tenant key, meant to live on the owner's site. No private/service keys are handled.
- All settings are sanitized on save (`agentnexlify_sanitize_settings`) and escaped again at render (`esc_url`/`esc_attr`) — defense in depth.
- Loader URL and API-base overrides are constrained to `https` URLs.
- Settings page is gated by `current_user_can('manage_options')`; the form uses the WordPress Settings API (nonce via `settings_fields`).

## Packaging for distribution

The installable zip is the **`agentnexlify/`** directory (WordPress expects the plugin folder at the zip root):

```bash
cd wordpress-plugin
zip -r agentnexlify.zip agentnexlify
```

Upload `agentnexlify.zip` via **Plugins → Add New → Upload Plugin**, or submit the `agentnexlify/` folder to the WordPress.org plugin directory.

## Local testing

1. Copy `agentnexlify/` into `wp-content/plugins/` of a local WordPress install.
2. Activate **AgentNexLiFy Chat Widget**.
3. Settings → AgentNexLiFy → paste a real `wk_...` key → Save.
4. Load the site front end; confirm the chat bubble appears and `<script ... data-api-key>` is present before `</body>` (view source).

Lint the PHP before shipping:

```bash
php -l wordpress-plugin/agentnexlify/agentnexlify.php
```
