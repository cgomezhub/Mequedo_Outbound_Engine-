#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

def run_script(script_name, args=[]):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)
    
    print(f"\n==================================================")
    print(f"🚀 Running: {script_name} {' '.join(args)}")
    print(f"==================================================")
    
    # Run the script with the same python interpreter
    cmd = [sys.executable, script_path] + args
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print(f"\n❌ Error: {script_name} failed with exit code {result.returncode}.", file=sys.stderr)
        sys.exit(result.returncode)
    
    print(f"✅ Finished: {script_name}")

def main():
    parser = argparse.ArgumentParser(description="Orchestrator for the Mequedo Outbound Engine pipeline.")
    parser.add_argument("--send", action="store_true", help="Run the sending stage immediately after drafting.")
    parser.add_argument("--dry-run", action="store_true", help="Draft emails and perform a dry-run of the sending stage (no emails sent).")
    args = parser.parse_args()

    # Step 1: Parse and research new contacts
    run_script("parse_contacts.py")

    # Step-2: Draft emails for new contacts
    run_script("write_emails.py")

    # Step 3: Optional sending / dry run
    if args.send:
        run_script("send_campaign.py")
    elif args.dry_run:
        run_script("send_campaign.py", ["--dry-run"])
    else:
        print("\n==================================================")
        print("🎉 Research and Drafting are complete!")
        print("Next steps:")
        print("1. Review/edit drafts in: data/hospitality-contacts-researched.csv")
        print("2. Run the sending script manually:")
        print("   python3 send_campaign.py")
        print("   (Or run the pipeline again with the --send flag: python3 run_pipeline.py --send)")
        print("==================================================")

if __name__ == "__main__":
    main()
