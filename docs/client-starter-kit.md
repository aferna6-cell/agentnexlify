# AgentNexLiFy Chat Widget -- Client Starter Kit

Welcome! This guide will walk you through adding the AgentNexLiFy chat widget to your website. The whole process takes about 5 minutes, and you do not need any coding experience.

When you are done, a small chat bubble will appear in the bottom-right corner of your website. Your visitors can click it to start a conversation, ask questions, and book appointments -- all handled automatically.

---

## What You Will Need

1. Your **API key** (provided by your AgentNexLiFy partner -- it looks something like `ak_abc123xyz`).
2. Access to your website editor or dashboard (wherever you normally make changes to your site).

---

## Your Embed Code

Copy the code below and replace `YOUR_API_KEY` with the actual API key you were given:

```html
<script src="https://agentnexlify.com/widget/agentnexlify-widget.js"
        data-api-key="YOUR_API_KEY"
        async>
</script>
```

That single snippet is all you need. The instructions below show you exactly where to paste it for your specific website platform.

---

## Installation by Platform

### 1. WordPress

1. Log in to your WordPress admin panel (usually `yoursite.com/wp-admin`).
2. In the left sidebar, go to **Appearance** then **Theme File Editor** (on older versions this may say "Theme Editor").
3. On the right side, find and click the file called **footer.php**.
4. Scroll to the bottom of that file. Look for the line that says `</body>`.
5. Paste your embed code on the blank line directly above `</body>`.
6. Click **Update File**.
7. Visit your website in a new tab to confirm the chat bubble appears.

> **Alternative (using a plugin):** If you are not comfortable editing theme files, install a free plugin called "Insert Headers and Footers" (by WPCode). Once activated, go to its settings page, paste your embed code into the **Footer** box, and save.

<!-- [Screenshot placeholder: WordPress footer.php editor with embed code highlighted] -->

### 2. Wix

1. Log in to your Wix dashboard.
2. Click **Settings** in the left sidebar.
3. Scroll down and click **Custom Code** (under the "Advanced" section).
4. Click the **Add Code** button (top right).
5. Paste your embed code into the code box.
6. Under "Place Code in," select **Body - end**.
7. Under "Add Code to Pages," select **All Pages**.
8. Give it a name like "AgentNexLiFy Chat Widget."
9. Click **Apply**.
10. Open your live site in a new tab to confirm.

<!-- [Screenshot placeholder: Wix custom code settings panel] -->

### 3. Squarespace

1. Log in to your Squarespace account and open your site.
2. Go to **Settings** then **Advanced** then **Code Injection**.
3. Scroll down to the box labeled **Footer**.
4. Paste your embed code into that Footer box.
5. Click **Save**.
6. Visit your website in a new tab to confirm the chat bubble appears.

<!-- [Screenshot placeholder: Squarespace Code Injection footer field] -->

### 4. Shopify

1. Log in to your Shopify admin panel.
2. In the left sidebar, go to **Online Store** then **Themes**.
3. Find your current theme and click **Actions** (or the three dots), then **Edit Code**.
4. In the file list on the left, open the **Layout** folder and click **theme.liquid**.
5. Scroll to the very bottom. Find the line that says `</body>`.
6. Paste your embed code on the blank line directly above `</body>`.
7. Click **Save**.
8. Visit your storefront in a new tab to confirm.

<!-- [Screenshot placeholder: Shopify theme.liquid editor with embed code] -->

### 5. Plain HTML Website

If your website is built with plain HTML files (or if a web developer manages it for you):

1. Open your main HTML file (usually called `index.html`) in any text editor.
2. Scroll to the very bottom. Find the line that says `</body>`.
3. Paste your embed code on the blank line directly above `</body>`.
4. Save the file and upload it to your web hosting.
5. Visit your website to confirm the chat bubble appears.

If you have multiple HTML pages and want the widget on all of them, repeat this for each page. If your site uses a shared template or layout file, you only need to add it there once.

---

## How to Know It Is Working

Once installed correctly, you will see:

- A **round chat bubble** in the bottom-right corner of your website.
- Clicking the bubble opens a chat window with a greeting message.
- The chat window shows your business name and branding colors.

<!-- [Screenshot placeholder: Chat bubble visible on a sample website] -->
<!-- [Screenshot placeholder: Chat window open showing greeting message] -->

### Quick Test

1. Open your website in a browser (use a private/incognito window for a fresh test).
2. Look for the chat bubble in the bottom-right corner.
3. Click the bubble to open the chat window.
4. Type **hi** and press Enter.
5. You should receive an automatic response within a few seconds.

If all of that works, you are all set.

---

## Troubleshooting

### I do not see the chat bubble on my site

- **Wait 1-2 minutes.** Some platforms (especially Wix and Squarespace) take a moment to publish changes.
- **Clear your browser cache.** Press Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac) to do a hard refresh.
- **Check that you replaced YOUR_API_KEY.** The code must contain your actual API key, not the placeholder text.
- **Make sure the code is before the closing body tag.** It should appear just above `</body>`, not inside the `<head>` section.
- **Try a different browser or incognito window.** Browser extensions (especially ad blockers) can sometimes hide the widget.

### The bubble appears but nothing happens when I click it

- Check your internet connection.
- Try in an incognito/private window to rule out browser extension interference.
- Contact support (see below) -- your API key may need to be activated.

### The bubble appears on my homepage but not on other pages

- On some platforms, custom code only applies to the homepage by default. Go back to the installation step for your platform and make sure you selected "All Pages" (Wix) or placed the code in a site-wide file (WordPress footer.php, Squarespace Code Injection, Shopify theme.liquid).

### I accidentally broke my website

- Do not panic. Go back to the editor where you pasted the code and remove the snippet you added. Save, and your site will go back to normal.

---

## Getting Help

If you run into any issues or have questions, reach out to us:

- **Email:** support@agentnexlify.com
- **Subject line:** Widget Installation Help -- [Your Business Name]

Include the following in your email so we can help you quickly:

1. Your business name
2. Your website address
3. What platform your site is on (WordPress, Wix, etc.)
4. A description of what you see (or do not see)

We typically respond within a few hours during business days.

---

That is it! Your chat widget is live and ready to help your customers around the clock.
