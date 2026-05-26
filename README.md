# Mequedo Outbound Engine

Welcome to the **Mequedo Outbound Engine**, an AI-driven, highly optimized B2B lead research and outbound email delivery system.

It uses specialized sub-agents powered by Google Gemini to research companies and write highly personalized cold outreach emails signed by Carlos Gomez, then dispatches them concurrently via the Resend API.

---

## 📂 Directory Structure

- **`data/`**
  - `seed-hospitality-contacts.csv`: Mock seed contacts to run the project out-of-the-box. Rename this to `hospitality-contacts-export.csv` to run tests.
  - `hospitality-contacts-export.csv` (ignored): Real B2B contacts uploaded from Apollo.
  - `hospitality-contacts-researched.csv` (ignored): The database sheet updated incrementally with research summaries, drafted emails, and sending status.
- **`parse_contacts.py`**: Executes the **`Researcher`** sub-agent concurrently to summarize prospects' business models from keywords.
- **`write_emails.py`**: Executes the **`Copywriter`** sub-agent concurrently to draft personalized cold outreach emails using the target research summary.
- **`send_campaign.py`**: Connects to the **Resend API** to log drafts, send validation test emails, or dispatch the final campaign.
- **`run_pipeline.py`**: The main orchestrator script to run the entire pipeline in sequence.

---

## ⚙️ Environment Configuration

Create a `.env` file in the root of the project with the following keys:

```env
GEMINI_API_KEY=AIzaSy...your_gemini_key
RESEND_API_KEY=re_...your_resend_key
```

### Required Dependencies

Install the required packages in your Python environment:

```bash
pip install pydantic python-dotenv resend
```

_(The `google-antigravity-sdk` is pre-installed in your agent workspace environments)._

---

## 🚀 Running the Engine

Before running the scripts, make sure you have a raw contacts sheet in the `data/` folder.

If you are running the project for the first time or demonstrating it with the seed data, rename the seed file:

```bash
cp data/seed-hospitality-contacts.csv data/hospitality-contacts-export.csv
```

The pipeline supports two workflows: **Incremental Manual Review** (recommended) or **Fully Automated End-to-End Delivery**.

### 1. Manual Review Workflow (Recommended)

This splits drafting and sending to ensure you can open the CSV, check the email drafts, and verify everything looks natural before any emails are sent.

**Step 1: Run research and drafting**

```bash
python3 run_pipeline.py
```

- Runs the `Researcher` agent on new rows to summarize business portfolios.
- Runs the `Copywriter` agent on new rows to write personalized cold drafts.
- _Skips any leads that have already been researched or drafted._

**Step 2: Inspect & Edit**
Open `data/hospitality-contacts-researched.csv` in Excel or Numbers. Review or refine any email subject/body drafts as needed.

**Step 3: Test Email Validation**
Send a test draft to your own inbox to verify rendering and layout:

```bash
python3 send_campaign.py --test-email youremail@contact.com
```

**Step 4: Dispatch the Campaign**
Send all verified drafts to your prospects via Resend:

```bash
python3 send_campaign.py
```

- Dispatches emails from `your name <youremail@mequedo.app>`.
- Marks `Email Sent` to `true` in the database to prevent duplicate sends.

---

### 2. Fully Automated Workflow (Direct Send)

If you want the engine to research, write, and immediately send emails to all unsent leads in the raw CSV, execute:

```bash
python3 run_pipeline.py --send
```

### 3. Dry-Run Verification

To preview what drafts will look like in the terminal console without hitting your Resend sending limits:

```bash
python3 run_pipeline.py --dry-run
```
