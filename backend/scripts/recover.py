import json

with open(r"C:\Users\USER\.gemini\antigravity\brain\a9051a8a-c2d5-42a6-a541-390c4450c4a3\.system_generated\logs\transcript_full.jsonl", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if "tool_calls" in data:
            for call in data["tool_calls"]:
                func = call.get("function", {})
                name = func.get("name", "")
                if name in ["multi_replace_file_content", "replace_file_content"]:
                    args_str = func.get("arguments", "{}")
                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        continue
                    if "prediction_engine.py" in args.get("TargetFile", ""):
                        print("FOUND EDIT:", args.get("Instruction", ""))
                        if "ReplacementChunks" in args:
                            for chunk in args["ReplacementChunks"]:
                                print(chunk.get("ReplacementContent", ""))
                        else:
                            print(args.get("ReplacementContent", ""))
                        print("="*80)
