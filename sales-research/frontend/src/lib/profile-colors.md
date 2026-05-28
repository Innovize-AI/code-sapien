# Profile Card Color System

| Color     | Condition                          |
|-----------|------------------------------------|
| Rose (bright) | Competitor (`is_competitor`)   |
| Emerald   | Fit — ICP match (`is_fit`)         |
| Violet    | Buy Signal (`is_buy_signal`)       |
| Blue      | Decision Maker (`is_decision_maker`) |
| Zinc      | Strategic Seller (`is_strategic_seller`) |
| Rose (muted) | Not Fit / Disqualified (`is_fit === false`, no other positive signal) |
| Zinc (light) | Unclassified — no signals set  |

Source: `src/components/profiles/profile-views-v2.tsx` → `getAccent()`
