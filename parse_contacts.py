#!/usr/bin/env python3
import asyncio
import csv
import os
import pydantic
from dotenv import load_dotenv
from google.antigravity import Agent, LocalAgentConfig

# Load environment variables from .env file
load_dotenv()

# Define the Pydantic schema for the Researcher Sub-Agent
class ResearcherOutput(pydantic.BaseModel):
    researcher_summary: str

# Define the Researcher Agent configuration
researcher_config = LocalAgentConfig(
    system_instructions=(
        "You are an expert B2B business researcher. Your goal is to analyze a "
        "string of comma-separated keywords about a hospitality company and "
        "summarize their core portfolio into one single, natural-sounding phrase "
        "(e.g., 'managing luxury oceanfront vacation rentals and private villas in Miami Beach').\n\n"
        "CRITICAL FORMAT RULES:\n"
        "1. Output ONLY the single natural-sounding phrase. E.g. starting with a gerund like 'managing...', 'operating...', or 'providing...'.\n"
        "2. Do NOT write any introduction (like 'Analyzed the keywords...' or 'Here is the summary:').\n"
        "3. Do NOT include markdown quotes or conversational filler."
    ),
    response_schema=ResearcherOutput,
)

async def analyze_keywords(keywords: str, retries: int = 3) -> str:
    if not keywords.strip():
        return "No keywords provided."
        
    for attempt in range(retries):
        try:
            # Open a fresh Agent session for each row
            async with Agent(config=researcher_config) as agent:
                response = await agent.chat(f"Keywords: {keywords}")
                output = await response.structured_output()
                
                if output and 'researcher_summary' in output:
                    summary = output['researcher_summary'].strip()
                    if summary:
                        return summary
                
                # Fallback if structured_output was not returned
                text = await response.text()
                text = text.strip()
                if text:
                    return text
                    
        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "quota" in err_str.lower()
            is_conn_closed = "1000" in err_str or "closed" in err_str.lower() or "websocket" in err_str.lower()
            
            if is_rate_limit or is_conn_closed:
                wait_time = 5 + (attempt * 5)
                reason = "Rate Limit" if is_rate_limit else "Connection Closed"
                print(f"\n[{reason}] Pausing for {wait_time}s before retry (Attempt {attempt + 1}/{retries})...")
                await asyncio.sleep(wait_time)
            else:
                return f"Error: {e}"
                
    return "Error: Exceeded maximum retries."

async def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'data', 'hospitality-contacts-export.csv')
    output_csv_path = os.path.join(script_dir, 'data', 'hospitality-contacts-researched.csv')

    # Check for Gemini API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY is not set in your environment or .env file.")
        print("Please obtain a Gemini API key from Google AI Studio:")
        print("https://aistudio.google.com/app/api-keys")
        print("\nThen, create a '.env' file in this directory with:")
        print("GEMINI_API_KEY=your_api_key_here")
        return

    # Step 1: Load existing summaries to enable incremental processing
    existing_summaries = {}
    if os.path.exists(output_csv_path):
        try:
            with open(output_csv_path, mode='r', encoding='utf-8') as outfile:
                out_reader = csv.DictReader(outfile)
                for row in out_reader:
                    email = row.get('Email', '').strip()
                    summary = row.get('Researcher Summary', '').strip()
                    if email and summary:
                        existing_summaries[email] = summary
            print(f"Loaded {len(existing_summaries)} existing summaries from: {output_csv_path}")
        except Exception as e:
            print(f"Warning: Could not read existing researched file: {e}")

    print(f"Reading contacts from: {csv_path}\n")

    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return

    try:
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            headers = list(reader.fieldnames) if reader.fieldnames else []
            contacts = list(reader)
            
            # Helper to run the task and assign the output to the row dictionary
            async def run_task(row):
                first_name = row.get('First Name', '').strip()
                last_name = row.get('Last Name', '').strip()
                company = row.get('Company Name', '').strip()
                keywords = row.get('Keywords', '').strip()
                email = row.get('Email', '').strip()

                full_name = f"{first_name} {last_name}".strip()
                
                if full_name and keywords:
                    # Check if already researched
                    if email in existing_summaries:
                        row['Researcher Summary'] = existing_summaries[email]
                        return
                    
                    # Otherwise, run research
                    summary = await analyze_keywords(keywords)
                    row['Researcher Summary'] = summary
                    print(f"[NEW] {full_name:<22} | {company:<30} | {summary}")
                else:
                    row['Researcher Summary'] = ""

            # Run all research tasks concurrently
            new_research_count = sum(1 for r in contacts if r.get('Email', '').strip() not in existing_summaries)
            if new_research_count > 0:
                print(f"Researching {new_research_count} new contacts...")
                print(f"{'Name':<22} | {'Company':<30} | {'Researcher Summary'}")
                print("-" * 120)
            else:
                print("No new contacts to research.")

            await asyncio.gather(*(run_task(row) for row in contacts))

            # Add Researcher Summary to fieldnames for the output file
            if 'Researcher Summary' not in headers:
                headers.append('Researcher Summary')

            # Write the results back to the output CSV file
            with open(output_csv_path, mode='w', encoding='utf-8', newline='') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(contacts)

            print(f"\nSuccessfully processed {len(contacts)} contacts (Reused: {len(contacts) - new_research_count}, Researched: {new_research_count}).")
            print(f"Saved researched data to: {output_csv_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
