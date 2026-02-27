# client.py 初始化client
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # 自动加载 .env

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# generate.py 提交生成任务
from client import client

prompt = "A cyberpunk cat wearing neon goggles rides a scooter through rainy Tokyo streets"

video_job = client.videos.create(
    model="sora-2",          # 或 "sora-2-pro"
    prompt=prompt,
    resolution="720x1280",   # 支持: 720x1280 / 1280x720 / 1920x1080
    duration=8,              # 4~10 秒（pro 支持 10s）
)

print(f"✅ 任务已提交，ID: {video_job.id}")
print(f"⚠️ 注意：视频不会立即返回，需轮询状态！")

# polling.py  轮询下载
import time
from client import client

def wait_for_video(video_id: str, poll_interval: int = 5, timeout: int = 600) -> dict:
    """
    轮询视频生成状态，支持超时与错误重试
    
    Returns:
        dict: 完整 job info（含 download_url）
    """
    start = time.time()
    while time.time() - start < timeout:
        job = client.videos.retrieve(video_id)
        
        print(f"[{int(time.time()-start)}s] 状态: {job.status} | 进度: {getattr(job, 'progress', 0)}%")
        
        if job.status == "completed":
            print("🎉 视频生成完成！")
            return job.to_dict()  # OpenAI 模型转 dict 更易处理
        
        if job.status == "failed":
            error_msg = getattr(job, "error", {}).get("message", "未知错误")
            raise RuntimeError(f"❌ 生成失败: {error_msg}")
        
        time.sleep(poll_interval)
    
    raise TimeoutError(f"⏱️ 轮询超时（>{timeout}s）")

# 示例调用
# job_info = wait_for_video("vid_abc123xyz789")