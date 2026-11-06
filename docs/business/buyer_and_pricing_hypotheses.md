# Buyer and Pricing Hypotheses

**Status: hypotheses, drafted 6 Nov 2026, before any customer conversation.** Nothing here is a finding. Each row says what would prove it wrong, and this page is meant to be replaced by interview evidence. Prizes and Azure credits are not revenue and are not counted anywhere below.

## 1. Who might pay

| # | Buyer (title) | The pain we think they have | How they would count the value | What would prove us wrong |
| --- | --- | --- | --- | --- |
| A | Agent builders: founder or engineering lead of a team whose agents buy, book or claim things | Their agents collide with each other or with other agents, and failures are not machine-readable | Fewer failed or duplicate attempts; engineer hours spent on retries | They say simple retries and idempotency keys already cover it |
| B | Marketplaces and commerce platforms: platform or infrastructure engineer, head of product | A burst of near-identical agent requests creates duplicate holds and load around limited items | Fewer duplicate holds and support tickets; protected inventory systems | They already use queues or waiting rooms and do not see agent traffic as separate |
| C | Booking, ticketing and capacity systems: operations or platform lead | One seat, slot or GPU must go to one requester, and agents make races more frequent | Avoided double bookings; smoother launches | Their own transactions already guarantee one winner and the pain is only load |
| D | Companies running many internal agents: AI platform team | Their own agents duplicate actions or fight over shared quotas and approvals | Duplicate actions prevented; a record of what each agent did | Their agent framework already coordinates this |
| E | Risk, finance or security teams: need proof an agent was allowed to spend | No clear record of which agent was authorised to do what | Audit readiness; fewer unauthorised actions | Payment and identity providers already cover it, or nobody asks |

Segments D and E use the same engine with a different pitch. If A to C fail, they are the first alternatives (see section 6).

## 2. Ways it could earn money

| Model | Charge for | Fits if | Main risk |
| --- | --- | --- | --- |
| Usage-based hosted service | Each successful lock (not each attempt) | Agent traffic grows and buyers see a lock as the unit of value | Volumes may stay small for a long time |
| Subscription with volume tiers | Monthly fee for platforms and vendors | Segment B or C has a recurring need | Long sales cycles |
| Free plan, paid extras | Signing, audit history, uptime guarantee, support | Segment A is the main user | Free users never convert |
| Open-source core, paid managed service | Hosting, enterprise sign-in, audit retention, support (the code is Apache-2.0, so anyone can self-host) | Running it themselves is a real hassle | Easy to copy and self-host |
| Paid pilots and integration work | A fixed fee for a 4 to 8 week pilot | Early: a buyer wants it working with their system | Does not scale; pulls toward custom work |

Likeliest first revenue: a paid pilot. Subscription or usage pricing comes after one buyer and one repeated pain are clear. A marketplace listing (for example on Azure) is a later possibility; its requirements are unverified.

## 3. How to set a price (without inventing one)

A price must satisfy three checks. Fill the blanks as the evidence arrives.

1. **Above our cost.** Cost per 1,000 locks = ______ (Cosmos DB + intent parsing + safety screening + hosting). Measured in the live Azure load test, not estimated.
2. **Below the buyer's cost of the problem.** Buyer's stated yearly cost of the problem = ______ (engineer hours x rate, lost sales). Taken from what interviewees say, not from us.
3. **A price someone will name.** Price points to test after 8 conversations: low ______ / middle ______ / high ______ per month. Choose them after checks 1 and 2.

## 4. Money questions for the conversations

Ask these after the problem questions, and only if the person described a real problem.

1. What happened the last time agents or automations collided? What did it cost you in time or lost business?
2. What do you do about it today? What does that cost?
3. Who would decide to spend money on fixing it, and who would sign?
4. Have you paid for anything to solve a similar problem? What, and how much?
5. If something solved this, how would you want to pay: per use, monthly, per agent, or a fixed project fee?
6. Would you run a 4 to 8 week pilot? What would it have to prove?
7. At roughly (price point), would you sign a letter of intent today? If not, what is missing?

## 5. What counts as evidence

- **Strong:** a named cost, a named buyer, and a willingness to sign a pilot or letter of intent at a stated price.
- **Weak:** "sounds interesting" and general agreement.
- Record each conversation as: segment, pain, current workaround, stated cost, would sign (yes, no, maybe), price named.

## 6. Decisions this page feeds

- **After 8 conversations (about 10 Dec):** pick the price points in section 3.
- **20 Dec wedge decision:** if three or more of 15 people describe the same problem and a workaround they dislike, build for that segment. If not, move to D or E and rerun 8 conversations by 15 Jan.
- **31 Jan:** one buyer, one pricing model and at least one letter of intent or pilot conversation, or say plainly in the submission that none exists yet.

## 7. Assumptions we are making, and should check

- Agent traffic against scarce resources will become common enough to matter. Unproven.
- Buyers will pay a third party for coordination instead of building it. Unproven.
- A lock only has value if the vendor checks it. Today it cannot; a signed lock token is planned.
- The code is Apache-2.0, so a managed service must be worth paying for compared with self-hosting.
