from src.core.engine import CoreEngine

def debug_adapter():
    engine = CoreEngine()
    print("Starting processing of 1 TC...")
    # You can just slice the parsed list inside process_file_stream?
    # No, we have to let it process. I'll just break after 1 TC manually.
    for event in engine.process_file_stream("data/mock_tc_data.tsv"):
        print(f"EVENT: {event}")
        if event.get("type") in ["success", "error"] and ("code_output" in event or "Adapter failed" in event.get("message", "")):
            if event.get("type") == "error":
                print(">>> ADAPTER ERROR ENCOUNTERED")
            break

if __name__ == "__main__":
    debug_adapter()
