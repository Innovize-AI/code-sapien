# Seed Users

All passwords: `SeedPass@123`

| Email                        | Role      | Firm                   | Firm ID                              |
|------------------------------|-----------|------------------------|--------------------------------------|
| admin@speedtolead.ai         | admin     | (all firms)            | —                                    |
| interior@speedtolead.ai      | counselor | Studio Luxe Interiors  | 7f6d92b4-d266-4313-a91d-0b349f5e89ba |
| realestate@speedtolead.ai    | counselor | Prestige Homes         | 52be1cba-b8d7-4915-a465-564fe90ca667 |
| solar@speedtolead.ai         | counselor | Greenfield Solar       | fa908f84-5633-4fde-95c0-957e72181b68 |

Re-seed anytime: `python backend/scripts/seed_users.py`

## Aparna Constructions

Created by `python backend/scripts/seed_aparna_logins.py` (run with `--dry-run` first to see what it will do).
Same password as above: `SeedPass@123`.

| Email                          | Role      | Sees                                                         |
|--------------------------------|-----------|--------------------------------------------------------------|
| aparna@speedtolead.ai          | counselor | Every Aparna conversation                                    |
| aparna.partner@speedtolead.ai  | agent     | Only the conversations on a channel partner's own numbers    |
| aparna.team@speedtolead.ai     | agent     | Only the conversations on a team member's own numbers        |

The two agents are tied to two sample people added to the Aparna firm. They see nothing until a WhatsApp
number is registered for them (Partners and team, then the person, then Register a number).
Agents are tied to a person ID, so re-run the script if you ever delete and re-create those people.
