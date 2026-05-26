#!/usr/bin/env python3
import argparse
import asyncio
import csv
import os
import pydantic
from dotenv import load_dotenv
from google.antigravity import Agent, LocalAgentConfig

# Load environment variables
load_dotenv()

# Define the Pydantic schema for Copywriter Sub-Agent output
class CopywriterOutput(pydantic.BaseModel):
    subject: str
    body: str

# Define the Copywriter Agent configuration with updated sender details
copywriter_config = LocalAgentConfig(
    system_instructions=(
        "You are an expert B2B copywriter. Your goal is to write a highly personalized, compelling outbound cold email to a hospitality executive.\n"
        "You will receive the recipient's first name, company name, and a short summary of their core portfolio.\n\n"
        "CRITICAL RULES:\n"
        "1. The email MUST be signed by: Carlos Gomez, Lead Engineer & Founder at Mequedo.app.\n"
        "2. The signature block should naturally include his LinkedIn profile URL: https://linkedin.com/in/cgomezdev.\n"
        "3. Address the recipient by their first name.\n"
        "4. Mentions their company name and references their core portfolio naturally using the provided summary.\n"
        "5. Proposes a quick, high-value proposition for Mequedo's outbound services (e.g. automating lead generation, booking campaigns, or partner outreach).\n"
        "6. Ends with a single, clear, low-friction call-to-action (e.g. 'Do you have 10 minutes for a brief call next Thursday?').\n"
        "7. Keeps the email concise (under 120 words), professional, and natural-sounding (no corporate jargon or aggressive sales pitches)."
    ),
    response_schema=CopywriterOutput,
)

async def draft_email(first_name: str, company: str, summary: str, retries: int = 3) -> tuple[str, str]:
    prompt = (
        f"Recipient Name: {first_name}\n"
        f"Company Name: {company}\n"
        f"Core Portfolio Summary: {summary}"
    )
    
    for attempt in range(retries):
        try:
            async with Agent(config=copywriter_config) as agent:
                response = await agent.chat(prompt)
                output = await response.structured_output()
                
                if output and 'subject' in output and 'body' in output:
                    return output['subject'].strip(), output['body'].strip()
                
                # Fallback parser if structured_output fails
                text = await response.text()
                lines = text.strip().split('\n')
                subject = f"Intro: Carlos from Mequedo"
                body = text.strip()
                for line in lines:
                    if line.lower().startswith("subject:"):
                        subject = line[8:].strip()
                        body = "\n".join([l for l in lines if not l.lower().startswith("subject:")]).strip()
                        break
                return subject, body
                
        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "quota" in err_str.lower()
            is_conn_closed = "1000" in err_str or "closed" in err_str.lower() or "websocket" in err_str.lower()
            
            if is_rate_limit or is_conn_closed:
                wait_time = 5 + (attempt * 5)
                print(f"\n[Warning] Pausing for {wait_time}s before retry (Attempt {attempt + 1}/{retries})...")
                await asyncio.sleep(wait_time)
            else:
                return "Failed Draft", f"Error: {e}"
                
    return "Failed Draft", "Error: Exceeded maximum retries."

async def main():
    parser = argparse.ArgumentParser(description="Generate outbound cold emails.")
    parser.add_argument("--force", action="store_true", help="Force regenerate drafts even if they already exist.")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'data', 'hospitality-contacts-researched.csv')

    # Check for Gemini API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY is not set in your environment or .env file.")
        print("Please obtain a Gemini API key from Google AI Studio:")
        print("https://aistudio.google.com/app/api-keys")
        print("\nThen, create a '.env' file in this directory with:")
        print("GEMINI_API_KEY=your_api_key_here")
        return

    if not os.path.exists(csv_path):
        print(f"Error: Researched CSV file not found at {csv_path}. Please run parse_contacts.py first.")
        return

    print(f"Reading researched contacts from: {csv_path}\n")

    try:
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            headers = list(reader.fieldnames) if reader.fieldnames else []
            contacts = list(reader)
            
            # Ensure new output headers exist
            for new_header in ['Email Subject', 'Email Body']:
                if new_header not in headers:
                    headers.append(new_header)
            
            async def run_task(row):
                first_name = row.get('First Name', '').strip()
                company = row.get('Company Name', '').strip()
                summary = row.get('Researcher Summary', '').strip()
                email_sent = row.get('Email Sent', '').strip().lower()
                existing_subject = row.get('Email Subject', '').strip()
                existing_body = row.get('Email Body', '').strip()
                
                # Eligibility check:
                # 1. Must have a research summary
                # 2. Must not have already been sent (Email Sent == true)
                # 3. Must not have an existing draft subject/body (unless --force is passed)
                if not summary:
                    return
                
                if email_sent == 'true':
                    return
                
                if existing_subject and existing_body and not args.force:
                    return
                
                print(f"Drafting email for: {first_name} ({company})...")
                subject, body = await draft_email(first_name, company, summary)
                
                row['Email Subject'] = subject
                row['Email Body'] = body
                print(f"[DRAFTED] {first_name} ({company}) | Subject: {subject}")

            # Count eligible contacts
            eligible_count = 0
            for r in contacts:
                summary = r.get('Researcher Summary', '').strip()
                email_sent = r.get('Email Sent', '').strip().lower()
                existing_subject = r.get('Email Subject', '').strip()
                existing_body = r.get('Email Body', '').strip()
                
                if summary and email_sent != 'true':
                    if not (existing_subject and existing_body) or args.force:
                        eligible_count += 1
            
            if eligible_count > 0:
                print(f"Generating drafts for {eligible_count} contacts...\n")
                await asyncio.gather(*(run_task(row) for row in contacts))
            else:
                print("No new contacts need email drafting. Use --force to regenerate existing drafts.")

            # Write updated data back to the researched CSV file
            with open(csv_path, mode='w', encoding='utf-8', newline='') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(contacts)

            print(f"\nSuccessfully updated {len(contacts)} contacts (Drafted: {eligible_count}).")
            print(f"Updated file saved to: {csv_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
