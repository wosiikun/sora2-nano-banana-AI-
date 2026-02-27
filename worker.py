"""
worker.py - 独立运行的API调用脚本
用法: python worker.py <task_id> <api_name> <prompt> <duration> <orientation> <style> <image_path>
"""
import sys
import json
import time
from datetime import datetime
from sora_api_clean import yuansora, yunwusora

LOG_FILE = "logs.json"

def read_logs():
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def write_log(task_id, msg):
    logs = read_logs()
    if task_id not in logs:
        logs[task_id] = {"logs": [], "status": "running", "result": None}
    
    ts = datetime.now().strftime("%H:%M:%S")
    logs[task_id]["logs"].append(f"[{ts}] {msg}")
    
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def write_result(task_id, status, result):
    logs = read_logs()
    if task_id not in logs:
        logs[task_id] = {"logs": [], "status": "running", "result": None}
    
    logs[task_id]["status"] = status
    logs[task_id]["result"] = result
    
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def run():
    task_id = sys.argv[1]
    api_name = sys.argv[2]
    prompt = sys.argv[3]
    duration = int(sys.argv[4])
    orientation = sys.argv[5]
    style = sys.argv[6] if len(sys.argv) > 6 else "none"
    image_path = sys.argv[7] if len(sys.argv) > 7 and sys.argv[7] != "None" else None
    
    write_log(task_id, f"🚀 开始 {api_name}")
    
    try:
        if api_name == "yuansora":
            api = yuansora()
            write_log(task_id, "📡 调用 yuansora API...")
            result = api.generate(prompt, duration, orientation, image_path)
        else:
            api = yunwusora()
            write_log(task_id, "📡 调用 yunwusora API...")
            result = api.generate(prompt, duration, orientation, style, image_path)
        
        if result["success"]:
            write_log(task_id, "✅ 生成成功")
            write_result(task_id, "success", result)
        else:
            write_log(task_id, f"❌ 失败: {result.get('error', '')}")
            write_result(task_id, "failed", result)
    
    except Exception as e:
        write_log(task_id, f"❌ 异常: {str(e)}")
        write_result(task_id, "failed", {"success": False, "error": str(e)})

if __name__ == "__main__":
    run()