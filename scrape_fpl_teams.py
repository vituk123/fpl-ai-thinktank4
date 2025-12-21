import aiohttp
import asyncio
import csv
import argparse
import sys
import os
from tqdm import tqdm
from aiohttp import ClientSession, ClientTimeout

# FPL API Endpoints
BASE_URL = "https://fantasy.premierleague.com/api/entry/{}/"
BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

async def fetch_team(session: ClientSession, team_id: int):
    """
    Fetches team details for a specific team ID.
    Returns a dict with processed data or None if not found/error.
    """
    url = BASE_URL.format(team_id)
    try:
        async with session.get(url) as response:
            if response.status == 200:
                try:
                    data = await response.json()
                    # Check if data is actually a valid dict with 'id'
                    if not isinstance(data, dict) or "id" not in data:
                        # Could be maintenance message
                        return None
                    return {
                        "id": data.get("id"),
                        "team_name": data.get("name"),
                        "manager_name": f"{data.get('player_first_name')} {data.get('player_last_name')}",
                        "region": data.get("player_region_name"),
                        "overall_points": data.get("summary_overall_points"),
                        "overall_rank": data.get("summary_overall_rank")
                    }
                except Exception:
                    # Failed to parse JSON (e.g. maintenance string)
                    return None
            elif response.status == 404:
                return None  # Team does not exist
            elif response.status == 429:
                # Rate limited, wait and retry (handled by caller logic if needed, or just skip)
                # For simplicity in this script, we'll return None but log it if we were doing more complex logic
                # Realistically, we should backoff. Let's return a special marker or just None for now.
                print(f"Rate limited on ID {team_id}")
                return None
            else:
                return None
    except Exception as e:
        return None

async def worker(queue: asyncio.Queue, session: ClientSession, results_list, pbar, lock):
    """
    Worker consumer to process team IDs from the queue.
    Accumulates results in a list for batch writing.
    """
    while True:
        try:
            team_id = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            # Queue is empty, worker is done
            break
        
        try:
            result = await fetch_team(session, team_id)
            if result:
                async with lock:
                    results_list.append(result)
        finally:
            queue.task_done()
            pbar.update(1)

async def main():
    parser = argparse.ArgumentParser(description="Scrape FPL Team Data")
    parser.add_argument("--start", type=int, default=1, help="Starting Team ID")
    parser.add_argument("--end", type=int, default=12000000, help="Ending Team ID (inclusive)")
    parser.add_argument("--output", type=str, default="fpl_teams.csv", help="Output CSV file")
    parser.add_argument("--concurrency", type=int, default=100, help="Max concurrent requests (higher for large jobs)")
    parser.add_argument("--checkpoint", type=str, default=None, help="Checkpoint file to resume from")
    parser.add_argument("--batch-size", type=int, default=100000, help="Process in batches and save periodically")
    
    args = parser.parse_args()
    
    # Setup CSV
    fieldnames = ["id", "team_name", "manager_name", "region", "overall_points", "overall_rank"]
    
    # Determine start position (for resume)
    start_pos = args.start
    file_mode = 'w'
    if args.checkpoint and os.path.exists(args.checkpoint):
        # Read last processed ID from checkpoint
        with open(args.checkpoint, 'r') as f:
            try:
                start_pos = int(f.read().strip()) + 1
                file_mode = 'a'  # Append mode
                print(f"Resuming from team ID: {start_pos}")
            except:
                pass
    
    # Check if output file exists (for append mode)
    file_exists = os.path.exists(args.output)
    
    # Setup results accumulator and lock for thread safety
    results_list = []
    lock = asyncio.Lock()
    
    # Process in batches to avoid memory issues
    total_ids = args.end - start_pos + 1
    batch_count = 0
    
    timeout = ClientTimeout(total=30)  # Increased timeout for large jobs
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for batch_start in range(start_pos, args.end + 1, args.batch_size):
            batch_end = min(batch_start + args.batch_size - 1, args.end)
            batch_size = batch_end - batch_start + 1
            batch_count += 1
            
            print(f"\nProcessing batch {batch_count}: IDs {batch_start} to {batch_end} ({batch_size} teams)")
            
            queue = asyncio.Queue()
            results_list.clear()
            
            # Populate queue for this batch
            for i in range(batch_start, batch_end + 1):
                queue.put_nowait(i)
            
            # Create workers
            tasks = []
            with tqdm(total=batch_size, desc=f"Batch {batch_count}") as pbar:
                for _ in range(args.concurrency):
                    task = asyncio.create_task(worker(queue, session, results_list, pbar, lock))
                    tasks.append(task)
                
                # Wait for queue to process
                await queue.join()
            
            # Cancel workers
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Write batch results to CSV
            print(f"Writing {len(results_list)} results to CSV...")
            with open(args.output, mode='a' if file_exists else 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                    file_exists = True
                writer.writerows(results_list)
            
            # Update checkpoint
            if args.checkpoint:
                with open(args.checkpoint, 'w') as f:
                    f.write(str(batch_end))
            
            # Count teams in file (more efficient way)
            try:
                with open(args.output, 'r', encoding='utf-8') as f:
                    total_teams = sum(1 for line in f) - 1  # Subtract header
                    print(f"Batch {batch_count} complete. Total teams found so far: {total_teams}")
            except:
                print(f"Batch {batch_count} complete. Found {len(results_list)} teams in this batch.")
            
            # Small delay between batches to avoid overwhelming the API
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScraping interrupted.")
        sys.exit(0)

