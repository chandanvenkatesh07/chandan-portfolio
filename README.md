# Chandan Venkatesh Portfolio

This is the source for [chandanvenkatesh.com](https://chandanvenkatesh.com). It uses plain HTML, CSS, and JavaScript and deploys through Vercel from the `main` branch.

## Review locally

From Terminal:

```bash
cd /Users/AI/chandan-ai-portfolio-preview
python3 -m http.server 4173
```

Then open [http://localhost:4173](http://localhost:4173) in a browser.

You can also open `index.html` directly, although the local server is the more reliable preview method.

## Files

- `index.html` contains the portfolio content and SEO metadata.
- `styles.css` contains the responsive visual system and light/dark themes.
- `script.js` contains the theme toggle, mobile navigation, header behavior, and email-copy interaction.
- `assets/` contains the profile image and downloadable résumé PDF.

## Launch direction

Use `chandanvenkatesh.com` as the canonical website. Redirect `chandanvenkatesh.dev` to the canonical domain so SEO and analytics are consolidated.

The Adaptive Storefront live-demo link is intentionally omitted because its current Vercel URL returns 404. The repository and public build notes remain linked.
