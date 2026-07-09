# Premium / paid feature audit

## What is already in the repo

- `app/payments.py` contains a Telegram Stars product catalog and payload helpers, but the bot does not yet register invoice, pre-checkout, or successful-payment handlers.
- The couple flow already has a post-free upsell path: after the man report, the user can add her own birth date and then open deeper blocks.
- Analytics events are already stored through `ReportsStore.track_event`, so premium funnel events can be measured without a new analytics system.
- Deep content exists for Moon, Venus, Mercury, Mars, portraits, a full couple map, and message hints.

## Gap

The current “premium” value is content-rich, but payment enforcement is not connected. The safest MVP is not to hide the whole product behind payment immediately. First measure intent on specific high-value blocks, then enable Stars only where users click.

## Implemented in this pass

- Added Jupiter calculation to every new report.
- Added a Jupiter block: “common growth horizon”. This is a good premium candidate because it extends the existing emotional/communication analysis into future, meaning, support and shared growth.
- Added Jupiter to the deep couple keyboard and full report.

## Recommended next MVP for paid access

1. Keep the free report and the “add yourself” bridge free.
2. Track clicks on each deep block (`product_block_opened`, already implemented).
3. Make only the full map + Jupiter/message pack paid with Telegram Stars.
4. Add purchase events:
   - `premium_invoice_opened`
   - `premium_payment_succeeded`
   - `premium_content_unlocked`
5. Store entitlements by `user_id`, `product_key`, and `report_id` so paid blocks survive bot restarts.

## Why Jupiter is a strong premium candidate

It is not just another planet button. It gives a higher-level promise: “where the couple can grow together”. That is easier to package as paid value than one more micro-description, especially if paired with an actionable next-step card.
