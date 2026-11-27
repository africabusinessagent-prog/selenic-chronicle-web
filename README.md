# Selenic Chronicle reader

The public web page for Selenic Chronicle, a reader for VIGOR's research notes on the Voynich manuscript. It's a single static `index.html` served by GitHub Pages. It has no build step.

Free folio previews are part of the page. Everything else comes from the Selenic Chronicle API (`selenic-chronicle-api`, private), whose address is `SELENIC_API_BASE` near the top of the page's script:

| Feature | API |
| --- | --- |
| Sign in with an emailed link | `POST /api/v1/auth/request-link`, `POST /api/v1/auth/session` |
| Subscription status | `GET /api/v1/entitlements/me` |
| Subscriber notes for each folio | `GET /api/v1/content/folios/{id}/notes` |
| Subscribe (Paddle Checkout) and Manage subscription | `GET /api/v1/billing/config`, `POST /api/v1/billing/portal` |
| Download my data and Delete account | `GET /api/v1/account/export`, `POST /api/v1/account/delete` |

**Paid content must never be added to this page or this repository.** The page is public, and so is its git history.

## Editing

- Open `index.html` in a browser to preview it. Without the API, signing in falls back to the free tier.
- `terms.html`, `privacy.html` and `refunds.html` are the legal pages. They're linked from the page footer and are required for Paddle's website approval.
- The page loads Paddle.js only when the API reports billing is configured.
- `africabusinessagent-prog.github.io` and `selenic-chronicle-web` hold identical copies of this site. Make each change in both until one is retired.
