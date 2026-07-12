# Nebula Cloud Storage — Internal Handbook

## Company Overview

Nebula Cloud Storage is a fictional company created for this training lab. It
was founded in 2019 and is headquartered in Amman, Jordan. The company
provides encrypted cloud storage for small and medium businesses in the MENA
region.

## Product Tiers

Nebula offers three subscription tiers:

1. **Comet** — 50 GB storage, single user, $4.99/month.
2. **Orbit** — 500 GB storage, up to 5 team members, $19.99/month.
3. **Galaxy** — 5 TB storage, unlimited team members, $79.99/month,
   includes priority support and daily automated backups.

## Refund Policy

Nebula offers a 14-day money-back guarantee on all new subscriptions. Refund
requests must be submitted through the account dashboard under "Billing > Request
Refund". Refunds are processed within 5 business days. Annual plans are refundable
only within the first 14 days; after that, only the unused months are non-refundable.

## Support Hours

The support team is available Sunday through Thursday, from 9 AM to 6 PM
Amman time (GMT+3). Galaxy plan customers get 24/7 support via live chat and a
dedicated Slack channel.

## Data Centers

Nebula operates three data centers:

- **DC-1**: Frankfurt, Germany (primary, serves Europe and MENA)
- **DC-2**: Manama, Bahrain (serves Gulf countries with low latency)
- **DC-3**: Singapore (serves Southeast Asia, added in 2023)

All data is encrypted at rest using AES-256 and in transit using TLS 1.3.

## Founding Team

Nebula was founded by three engineers: Lina Haddad (CEO), Omar Fares (CTO), and
Yousef Al-Rashid (VP of Engineering). The founding team previously worked together
at a regional telecom company before starting Nebula in a co-working space in
Amman.

## A Note for This Lab

The two facts below exist only in this document — a general-purpose language model
has never seen them in its training data. They are used in `04_rag_demo.py` to prove
that the answer comes from retrieval, not from the model's prior knowledge:

- Nebula's support ticket system is internally called **"Comet Desk"**.
- The internal codename for Nebula's 2024 infrastructure migration project was
  **"Project Halyard"**.
