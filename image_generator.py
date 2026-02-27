"""
GrsAI API 图片生成模块
"""
import time
import requests
from pathlib import Path
import uuid
import streamlit as st


API_KEY = "sk-ca999d825073499cbe1a0a724f91461c"
API_HOST = "https://grsai.dakka.com.cn"
TIMEOUT = 300


def generate_id():
    return str(uuid.uuid4())[:8]


def download_image(image_url, save_path):
    """下载图片到指定路径"""
    response = requests.get(image_url, timeout=60)
    response.raise_for_status()
    
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(save_path, "wb") as f:
        f.write(response.content)
    
    return save_path


def poll_result(task_id):
    """轮询任务结果"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    start_time = time.time()
    last_progress = -1
    
    progress_placeholder = st.empty()
    
    while True:
        if time.time() - start_time > TIMEOUT:
            raise TimeoutError(f"生成超时（{TIMEOUT}秒）")
        
        response = requests.post(
            f"{API_HOST}/v1/draw/result",
            json={"id": task_id},
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("code") != 0:
            raise Exception(f"查询失败: {result.get('msg')}")
        
        data = result["data"]
        status = data.get("status")
        progress = data.get("progress", 0)
        
        if progress != last_progress:
            progress_placeholder.progress(progress / 100, text=f"生成中... {progress}%")
            last_progress = progress
        
        if status == "succeeded":
            progress_placeholder.empty()
            return data
        
        elif status == "failed":
            error = f"{data.get('failure_reason')}: {data.get('error')}"
            raise Exception(error)
        
        time.sleep(2)


def generate_image(prompt, model="nano-banana-fast", aspect_ratio="1:1", image_size="1K", save_path=None):
    """生成图片"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    if model in ["sora-image", "gpt-image-1.5"]:
        payload = {
            "model": model,
            "prompt": prompt,
            "size": aspect_ratio,
            "variants": 1,
            "webHook": "-1",
            "shutProgress": False
        }
        endpoint = f"{API_HOST}/v1/draw/completions"
    else:
        payload = {
            "model": model,
            "prompt": prompt,
            "aspectRatio": aspect_ratio,
            "imageSize": image_size,
            "webHook": "-1",
            "shutProgress": False
        }
        endpoint = f"{API_HOST}/v1/draw/nano-banana"
    
    response = requests.post(
        endpoint,
        json=payload,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()
    
    result = response.json()
    if result.get("code") != 0:
        raise Exception(f"API 错误: {result.get('msg')}")
    
    task_id = result["data"]["id"]
    
    data = poll_result(task_id)
    
    if model in ["sora-image", "gpt-image-1.5"]:
        image_url = data.get("url")
    else:
        results = data.get("results", [])
        if not results:
            raise Exception("未获取到图片")
        image_url = results[0].get("url")
    
    if not image_url:
        raise Exception("未获取到图片 URL")
    
    if not save_path:
        save_path = f"temp_{generate_id()}.png"
    
    return download_image(image_url, save_path)