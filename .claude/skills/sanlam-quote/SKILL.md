---
name: sanlam-quote
description: Price Sanlam funeral cover with the pricing engine. Use when quoting a premium, listing cover options, or writing chat copy, UI options, or directives that mention cover amounts, premiums, age limits, or plan minimums.
---
`execution/pricing_engine.py` is the single source of truth for prices.

- Cover options: `get_available_covers(category)`. Offer exactly these amounts.
- Eligibility, per life: `validate_eligibility(age, category, cover)`. Refer the application on `False`.
- Quote: `calculate_total_premium(lives, plan)`, where `plan` is `'value'` or `'all_in_one'`. Show `total`; it already applies the plan minimum.
- Numbers in copy come from `AGE_LIMITS`, `COVER_LIMITS`, `MIN_PREMIUMS`.

Current options:
```bash
python3 -c "from execution.pricing_engine import get_available_covers as g; [print(c, g(c)) for c in ('principal','spouse','child','parent','wider_family')]"
```

Report to the user any amount that a directive, UI, or brief lists but the engine lacks. The engine rounds unknown amounts up to the next row and quotes that row's premium.
Check child cover against the age-based legal limits in `directives/sanlam_all_in_one.md`; the engine does not apply them yet.
