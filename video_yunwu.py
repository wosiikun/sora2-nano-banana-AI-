"""
云雾平台视频生成器 - Sora2-all模型
"""
import streamlit as st
import requests
import time
from pathlib import Path


class VideoYunwuGenerator:
    """云雾平台视频生成器"""
    
    def __init__(self):
        """
        初始化视频生成器
        API密钥已写死在代码中
        """
        self.api_key = "sk-C4DhYzeXWyq0C1gOfgINHqpXsfABGsU5wU2ucBQXRi8Y3T1v"  # 在这里填写你的API密钥
        self.api_host = "https://yunwu.ai"  # 根据实际API地址修改
        self.timeout = 600  # 视频生成超时时间（秒）
    
    def poll_result(self, task_id):
        """轮询任务结果"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        start_time = time.time()
        last_progress = -1
        
        progress_placeholder = st.empty()
        
        while True:
            if time.time() - start_time > self.timeout:
                raise TimeoutError(f"生成超时（{self.timeout}秒）")
            
            # 查询任务状态
            response = requests.get(
                f"{self.api_host}/v1/video/create",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("code") != 0:
                raise Exception(f"查询失败: {result.get('msg')}")
            
            data = result.get("data", {})
            status = data.get("status")
            progress = data.get("progress", 0)
            
            if progress != last_progress:
                progress_placeholder.progress(progress / 100, text=f"视频生成中... {progress}%")
                last_progress = progress
            
            if status == "completed" or status == "succeeded":
                progress_placeholder.empty()
                return data
            
            elif status == "failed":
                error = f"{data.get('error', '生成失败')}"
                raise Exception(error)
            
            time.sleep(3)  # 轮询间隔
    
    def download_video(self, video_url, save_path):
        """下载视频到指定路径"""
        response = requests.get(video_url, timeout=120, stream=True)
        response.raise_for_status()
        
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return save_path
    
    def generate(self, image_url, prompt, duration=5, save_path=None):
        """
        生成视频(图生视频)
        
        Args:
            image_url: 参考图片URL
            prompt: 视频生成提示词
            duration: 视频时长(秒)
            save_path: 保存路径
        
        Returns:
            str: 视频文件路径
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 提交生成任务
        payload = {
            "model": "sora2-all",
            "image_url": image_url,
            "prompt": prompt,
            "duration": duration
        }
        
        endpoint = f"{self.api_host}/v1/video/create"
        
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
        
        task_id = result.get("data", {}).get("task_id") or result.get("data", {}).get("id")
        
        if not task_id:
            raise Exception("未获取到任务ID")
        
        # 轮询结果
        data = self.poll_result(task_id)
        
        # 获取视频URL
        video_url = data.get("video_url") or data.get("url") or data.get("result_url")
        
        if not video_url:
            raise Exception("未获取到视频 URL")
        
        if not save_path:
            save_path = f"temp_video_{int(time.time())}.mp4"
        
        return self.download_video(video_url, save_path)
