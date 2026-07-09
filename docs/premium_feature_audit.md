# Premium / paid feature audit

## What is already in the repo

- `app/payments.py` contains a Telegram Stars product catalog and payload helpers, but the bot does not yet register invoice, pre-checkout, or successful-payment handlers.
- The couple flow already has a post-free upsell path: after the man report, the user can add her own birth date and then open deeper blocks.
- Analytics events are already stored through `ReportsStore.track_event`, so premium funnel events can be measured without a new analytics system.
- Deep content exists for Moon, Venus, Mercury, Mars, portraits, a full couple map, and message hints.

## Product / market research notes

- Telegram Stars are the native Telegram currency for bots and mini apps that sell digital products.
- Modern paywalls work better when they show a concrete outcome, a short value ladder and a low-friction next action instead of listing every internal feature.
- For a relationship bot, the paid moment should happen after the user has already received a personal “aha”: the free key and the couple bridge. Charging before that would reduce trust.

## Gap fixed

The previous “premium” value was content-rich, but payment enforcement was not connected. The new MVP keeps the emotional key and several deep blocks free, then gates only the highest-intent actions:

1. **Premium-карта пары** — the complete pair map and relationship portraits.
2. **Premium-сообщение партнёру** — ready-to-send AI message variants.

This avoids a harsh paywall while still asking for payment exactly where intent is strongest.

## Implemented in this pass

- Added Jupiter calculation to every new report.
- Added a Jupiter block: “common growth horizon”. This is a good premium candidate because it extends the existing emotional/communication analysis into future, meaning, support and shared growth.
- Added Jupiter to the deep couple keyboard and full report.
- Reordered the post-bridge product menu into a guided sequence: emotions → warmth → communication → action → shared growth → paid map/message.
- Added Telegram Stars invoice flow for the two premium products.
- Added persistent premium entitlements by `user_id`, `product_key`, and `report_id`.
- Added premium funnel analytics events:
  - `premium_paywall_viewed`
  - `premium_gate_hit`
  - `premium_invoice_opened`
  - `premium_precheckout_approved`
  - `premium_payment_succeeded`

## Recommended next MVP for paid access

1. Add a simple admin export for premium funnel metrics by day.
2. A/B test two offers:
   - “Premium-карта пары” at 25 Stars.
   - “Что написать партнёру” at 15 Stars.
3. Add one post-payment success screen that immediately recommends the best first premium block based on the user’s previous click.
4. If message purchases convert better than the map, bundle both into one “Сделать мягкий шаг” offer.

## Why Jupiter is a strong premium candidate

It is not just another planet button. It gives a higher-level promise: “where the couple can grow together”. That is easier to package as paid value than one more micro-description, especially if paired with an actionable next-step card.
