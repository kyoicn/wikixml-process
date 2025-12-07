import argparse
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from parser import process_xml

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(CURRENT_DIR, "../data/raw/sample.xml")
OUTPUT_FILE = os.path.join(CURRENT_DIR, "../data/processed/output.json")

def main():
    parser = argparse.ArgumentParser(description="Extract Wikipedia data from XML dump.")
    parser.add_argument("input_file", nargs='?', default=INPUT_FILE, help="Path to input XML file")
    parser.add_argument("output_file", nargs='?', default=OUTPUT_FILE, help="Path to output JSON file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        sys.exit(1)
        
    print(f"Processing '{args.input_file}'...")
    
    data = []
    count = 0
    try:
        for entry in process_xml(args.input_file):
            data.append(entry)
            count += 1
            if count % 1000 == 0:
                print(f"Processed {count} pages...", end='\r')
                
        print(f"\nFinished processing. Total pages: {count}")

        if data:
            print("Last processed item:")
            print(json.dumps(data[-1], indent=2, ensure_ascii=False))
        
        print(f"Writing to '{args.output_file}'...")
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print("Done.")
        
    except Exception as e:
        print(f"\nError during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
