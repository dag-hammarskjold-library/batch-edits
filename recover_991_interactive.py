"""Interactive recovery of missing 991$e values from record history"""

import sys
from argparse import ArgumentParser
from dlx import DB
from dlx.marc import BibSet, Query

def get_args():
    parser = ArgumentParser()
    parser.add_argument('--connect', required=True, help='DLX connection string')
    parser.add_argument('--database', help='The database name')
    parser.add_argument('--querystring', required=True, help='DLX query string to find affected records')
    return parser.parse_args()

def find_most_recent_value(bib):
    """Search record history for the most recent version containing a 991$e value."""
    try:
        # Assuming the ODM provides a history method that returns historical Bib objects
        history = bib.history() 
        if not history:
            return None, None

        # History is typically newest first. Search for the first occurrence of 991$e.
        for version in history:
            field_991 = version.get_field('991')
            if field_991:
                val_e = field_991.get_value('e')
                if val_e:
                    # Try to get date of this version if available
                    date = getattr(version, 'timestamp', 'Unknown Date')
                    return val_e, date
    except Exception as e:
        print(f"Error accessing history for {bib.id}: {e}")
    
    return None, None

def main():
    args = get_args()
    DB.connect(args.connect, database=args.database)

    query = Query.from_string(args.querystring)
    bibs = BibSet.from_query(query)
    
    candidates = []
    for bib in bibs:
        # Surgical check: has 991 but missing $e
        field_991 = bib.get_field('991')
        if field_991 and not field_991.get_value('e'):
            candidates.append(bib)

    if not candidates:
        print("No records found matching the criteria (991 present, 991$e missing).")
        return

    print(f"Found {len(candidates)} records missing 991$e. Starting interactive recovery...")
    
    pending_updates = []
    
    try:
        for bib in candidates:
            # Handle potentially multiple 991 fields
            fields_991 = bib.get_fields('991')
            for field in fields_991:
                if not field.get_value('e'):
                    val_e, date = find_most_recent_value(bib)
                    
                    if not val_e:
                        print(f"Record {bib.id}: No 991$e value found in history. Skipping.")
                        continue
                    
                    print(f"\nRecord {bib.id}")
                    print(f"  Current 991: {field.to_mrk()}")
                    print(f"  Proposed 991$e: '{val_e}' (Found in history from {date})")
                    
                    choice = input("  Restore this value? [Y/n/s (skip)/q (quit)]: ").lower()
                    if choice == 'q':
                        print("Quitting interactive session...")
                        # We don't break here to allow handling the pending_updates later
                        # but we should stop processing new candidates.
                        candidates = [] # Stop loop
                        break
                    elif choice == 'y' or choice == '':
                        # Stage the update: (bib, field, value)
                        pending_updates.append((bib, field, val_e))
                        print("  Staged for update.")
                    else:
                        print("  Skipped.")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    if not pending_updates:
        print("\nNo updates staged. Exiting.")
        return

    print(f"\n--- Recovery Summary ---")
    print(f"You have staged {len(pending_updates)} updates across {len({b.id for b, f, v in pending_updates})} records.")
    
    confirm = input("Commit these changes to the database? [Y/n]: ").lower()
    if confirm == 'y' or confirm == '':
        updated_count = 0
        for bib, field, value in pending_updates:
            try:
                # Use ODM to set value and commit
                field.set('e', value)
                bib.commit(user='recovery_tool')
                updated_count += 1
            except Exception as e:
                print(f"Error committing record {bib.id}: {e}")
        
        print(f"Successfully updated {updated_count} records.")
    else:
        print("Changes discarded.")

if __name__ == '__main__':
    main()
