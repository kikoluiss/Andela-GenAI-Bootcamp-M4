# Test Contract Image Pairs

This folder contains two pairs of realistic, synthetic contract images to be used as input for the multimodal contract comparison agents.

All company names, parties, and terms are fictional and generated for demonstration purposes only.

---

## Pair 1: `contract1_original.png` and `contract1_amendment.png`

**Scenario:** SaaS Subscription Agreement between Acme Cloud Services, Inc. (Provider) and Example Retail Ltd. (Customer).

**Key changes in the amendment:**

- **Subscription fee increase**: Monthly subscription fee increases from **USD 10,000** to **USD 13,500**.
- **Payment terms**: Payment deadline is shortened from **30 days** to **15 days** from the invoice date.
- **Late payment interest**: Late payment interest rate increases from **1.0% per month** to **1.5% per month**.
- All other terms remain unchanged.

These differences should lead your agents to flag changes in the sections dealing with **fees**, **payment terms**, and **late interest**.

---

## Pair 2: `contract2_original.png` and `contract2_amendment.png`

**Scenario:** Master Services Agreement (MSA) between Northwind Analytics GmbH (Provider) and Global Manufacturing Co. (Client).

**Key changes in the amendment:**

- **Termination for convenience**:
  - Originally, either party could terminate the Agreement on **90 days' written notice**.
  - In the amendment, **Client** may terminate for convenience on **30 days' notice**, while **Provider** still must give **90 days' notice**.
- **Data retention period**:
  - Originally, Provider retained Client Data for **30 days** after termination.
  - In the amendment, retention is extended to **90 days**, and Client may request an **export of Client Data** in a mutually agreed format before deletion.

These differences should lead your agents to flag changes in the sections related to **termination rights**, **asymmetry of notice periods**, and **data retention/export obligations**.

---

You can use these images to validate:
- Image parsing of realistic, scanned-style contracts.
- Section alignment between original and amended documents.
- Extraction of high-level topics (fees, termination, data retention) and concise change summaries.