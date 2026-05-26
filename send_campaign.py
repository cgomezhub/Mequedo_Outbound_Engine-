#!/usr/bin/env python3
import argparse
import csv
import os
import resend
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_email(api_key: str, to_email: str, subject: str, body: str) -> bool:
    try:
        resend.api_key = api_key
        
        # Use plain text for cold outbound to ensure it renders as a personal 1-on-1 email
        params = {
            "from": "Carlos Gomez <cgomezlugo@contact.mequedo.app>",
            "to": to_email,
            "subject": subject,
            "text": body
        }
        
        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Error sending to {to_email}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Send outbound email campaigns using Resend.")
    parser.add_argument("--dry-run", action="store_true", help="Print email drafts to console without sending.")
    parser.add_argument("--test-email", type=str, metavar="EMAIL", help="Send a single test email from the list to this address.")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'data', 'hospitality-contacts-researched.csv')

    # Verify Resend API Key if not in dry-run
    resend_api_key = os.environ.get("RESEND_API_KEY")
    if not resend_api_key and not args.dry_run:
        print("Error: RESEND_API_KEY is not set in your environment or .env file.")
        print("Please add RESEND_API_KEY=your_resend_key to your .env file.")
        return

    if not os.path.exists(csv_path):
        print(f"Error: Researched CSV file not found at {csv_path}. Please run parse_contacts.py and write_emails.py first.")
        return

    print(f"Reading contacts from: {csv_path}\n")

    try:
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            headers = list(reader.fieldnames) if reader.fieldnames else []
            contacts = list(reader)

        # Ensure Email Sent header exists
        if 'Email Sent' not in headers:
            headers.append('Email Sent')

        # Mode A: Test Email Mode
        if args.test_email:
            # Find the first contact that has a drafted email
            test_contact = None
            for row in contacts:
                if row.get('Email Subject', '').strip() and row.get('Email Body', '').strip():
                    test_contact = row
                    break
            
            if not test_contact:
                print("Error: No drafted emails found in CSV. Please run write_emails.py first.")
                return

            subject = test_contact['Email Subject']
            body = test_contact['Email Body']
            first_name = test_contact.get('First Name', 'there')
            company = test_contact.get('Company Name', 'your company')

            print(f"Sending test email to: {args.test_email}")
            print(f"Draft source contact: {first_name} ({company})")
            print(f"Subject: {subject}\n")
            print("--- Email Body ---")
            print(body)
            print("------------------")

            success = send_email(resend_api_key, args.test_email, subject, body)
            if success:
                print("\n[SUCCESS] Test email sent successfully via Resend!")
            else:
                print("\n[FAILURE] Failed to send test email.")
            return

        # Mode B: Dry Run or Real Dispatch Mode
        eligible_contacts = []
        for row in contacts:
            subject = row.get('Email Subject', '').strip()
            body = row.get('Email Body', '').strip()
            email_sent = row.get('Email Sent', '').strip().lower()

            if subject and body and email_sent != 'true':
                eligible_contacts.append(row)

        if not eligible_contacts:
            print("No new email drafts found to send.")
            return

        if args.dry_run:
            print(f"--- Dry Run: Showing {len(eligible_contacts)} unsent email drafts ---")
            for index, row in enumerate(eligible_contacts):
                name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                company = row.get('Company Name', '')
                to_email = row.get('Email', '')
                subject = row.get('Email Subject', '')
                body = row.get('Email Body', '')

                print(f"\n[{index + 1}/{len(eligible_contacts)}] To: {name} <{to_email}> ({company})")
                print(f"Subject: {subject}")
                print("--- Body ---")
                print(body)
                print("-" * 50)
            print(f"\nDry Run finished. No emails were sent.")
            return

        # Mode C: Real Sending Mode
        print(f"Starting dispatch of {len(eligible_contacts)} emails...")
        sent_count = 0
        for row in eligible_contacts:
            to_email = row.get('Email', '').strip()
            subject = row.get('Email Subject', '').strip()
            body = row.get('Email Body', '').strip()
            name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()

            print(f"Sending to {name} <{to_email}>...", end="", flush=True)
            success = send_email(resend_api_key, to_email, subject, body)
            if success:
                row['Email Sent'] = 'true'
                sent_count += 1
                print(" [SENT]")
            else:
                print(" [FAILED]")

        # Save the updated status back to the CSV file
        with open(csv_path, mode='w', encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(contacts)

        print(f"\nSuccessfully finished campaign! Sent: {sent_count}/{len(eligible_contacts)} emails.")
        print(f"Updated status saved to: {csv_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
