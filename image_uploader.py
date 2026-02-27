"""
图片上传中转模块
用于将本地图片上传到服务器并获取URL
"""
import requests
from pathlib import Path


def upload_image_to_server(image_path, server_url):
    """
    上传图片到中转服务器
    
    Args:
        image_path: 本地图片路径
        server_url: 服务器地址 (例如: https://your-server.com)
    
    Returns:
        str: 图片URL
    """
    try:
        # 构建上传端点
        upload_url = f"{server_url.rstrip('/')}/upload/image"
        
        # 打开图片文件
        with open(image_path, 'rb') as f:
            files = {
                'image': (Path(image_path).name, f, 'image/png')
            }
            
            # 发送上传请求
            response = requests.post(
                upload_url,
                files=files,
                headers={"ngrok-skip-browser-warning": "true"},
                timeout=60
            )
        
        # 检查响应
        if response.status_code == 200:
            result = response.json()
            
            # 假设返回格式: {"url": "https://..."}
            # 根据你的实际API调整
            image_url = result.get('url') or result.get('data', {}).get('url')
            
            if image_url:
                return image_url
            else:
                raise Exception(f"响应中未找到URL: {result}")
        else:
            raise Exception(f"上传失败: HTTP {response.status_code}")
    
    except Exception as e:
        raise Exception(f"图片上传失败: {e}")


def upload_multiple_images(image_paths, server_url):
    """
    批量上传图片
    
    Args:
        image_paths: 图片路径列表
        server_url: 服务器地址
    
    Returns:
        list: 图片URL列表
    """
    urls = []
    
    for image_path in image_paths:
        try:
            url = upload_image_to_server(image_path, server_url)
            urls.append(url)
            print(f"✅ 已上传: {Path(image_path).name} → {url}")
        except Exception as e:
            print(f"❌ 上传失败 {Path(image_path).name}: {e}")
            urls.append(None)
    
    return urls