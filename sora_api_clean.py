"""
Sora-2 API 简洁封装类
包含：云雾API、自定义API、角色创建、错误处理规则、中转上传
"""
import requests
import time
from typing import Optional, Dict
from pathlib import Path
# import sys
# import io
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ==================== API配置管理 ====================
API_CONFIG = {
    "yunwusora": {
        "api_key": "sk-C4DhYzeXWyq0C1gOfgINHqpXsfABGsU5wU2ucBQXRi8Y3T1v",
        "base_url": "https://yunwu.ai"
    },
    "yuansora": {
        "api_key": "sk-dJCw1lROMxOQVoAOG8C3N7yzwksQF6iFAkVefiDruKHOq4Dl",
        "api_host": "45.205.26.177",
        "api_port": 9999
    },
    "yunwujuese": {
        "api_key": "sk-C4DhYzeXWyq0C1gOfgINHqpXsfABGsU5wU2ucBQXRi8Y3T1v",
        "base_url": "https://yunwu.ai"
    },
    
    # 中转服务器配置
    "upload_servers": {
        "image": "http://43.143.145.118:8085",
        "video": "http://43.143.145.118:8086"
    }
}


# ==================== 错误处理规则 ====================
ERROR_RULES = {
    "yuansora": {
        "儿童": {"action": "prompt_error", "message": "检测到儿童相关内容，请修改提示词"},
        "上游": {"action": "switch_to", "target": "yunwusora"},
    },
    "yunwusora": {
        "heavy load": {"action": "switch_to", "target": "yuansora"},
        "上游": {"action": "switch_to", "target": "yuansora"},
    }
}

def get_error_action(api_name: str, error_message: str) -> Dict:
    """根据API名称和错误信息返回处理动作"""
    if api_name not in ERROR_RULES:
        return {"action": "unknown", "message": error_message}
    
    for keyword, rule in ERROR_RULES[api_name].items():
        if keyword in error_message:
            return rule
    
    return {"action": "unknown", "message": error_message}


# ==================== API类 ====================

class yunwusora:
    """云雾API视频生成类"""
    
    def __init__(self):
        cfg = API_CONFIG["yunwusora"]
        self.api_key = cfg["api_key"]
        self.base_url = cfg["base_url"]
    
    def _upload_to_relay(self, file_path: str, file_type: str) -> str:
        """
        上传文件到中转服务器（与已跑通代码一致）
        file_type: 'image' 或 'video'
        返回: URL(成功) 或 原路径(失败)
        """
        try:
            server = API_CONFIG["upload_servers"][file_type]
            upload_url = f"{server}/upload/{file_type}"
            
            filename = Path(file_path).name
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            files = {
                file_type: (filename, file_data, 'video/mp4' if file_type == 'video' else 'image/jpeg')
            }
            
            response = requests.post(
                upload_url,
                files=files,
                headers={"ngrok-skip-browser-warning": "true"},
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                url = result.get('url') or result.get('data', {}).get('url')
                print(f"[OK] {file_type} 上传成功: {url}")  # 改这里
                return url
            else:
                print(f"[WARN] {file_type} 上传失败 (HTTP {response.status_code}), 使用本地路径")  # 改这里
                return file_path
        except Exception as e:
            print(f"[WARN] {file_type} 上传异常: {str(e)}, 使用本地路径")  # 改这里
            return file_path
    
    def generate(self, prompt: str, duration: int, orientation: str, style: str, 
                 image_file_path: Optional[str] = None, watermark: bool = False) -> Dict:
        
        size = "720x1280" if orientation == "portrait" else "1280x720"
        
        files_data = {
            'model': (None, 'sora-2-all'),
            'prompt': (None, prompt),
            'seconds': (None, str(duration)),
            'size': (None, size),
            'watermark': (None, str(watermark).lower())
        }
        
        if image_file_path:
            # 尝试上传到中转服务器
            processed_path = self._upload_to_relay(image_file_path, 'image')
            
            # 无论上传成功与否，都处理文件
            if processed_path.startswith('http'):
                # 从URL下载
                img_response = requests.get(processed_path)
                file_data = img_response.content
            else:
                # 从本地读取
                with open(processed_path, 'rb') as f:
                    file_data = f.read()
            
            files_data['input_reference'] = (image_file_path, file_data, 'image/jpeg')
        
        if style and style != 'none':
            files_data['style'] = (None, style)
        
        response = requests.post(
            f"{self.base_url}/v1/videos",
            files=files_data,
            headers={'Authorization': f'Bearer {self.api_key}'},
            timeout=180
        )
        
        if response.status_code != 200:
            return {"success": False, "error": response.text, "task_id": None}
        
        task_id = response.json().get("id")
        
        # 轮询
        for _ in range(60):
            time.sleep(10)
            
            query_response = requests.get(
                f"{self.base_url}/v1/videos/{task_id}",
                headers={
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                },
                timeout=30
            )
            
            if query_response.status_code == 200:
                result = query_response.json()
                status = result.get('status')
                
                if status == 'SUCCESS':
                    return {
                        "success": True,
                        "video_url": result.get('data', {}).get('video_url', ''),
                        "task_id": task_id
                    }
                elif status == 'FAILURE':
                    return {
                        "success": False,
                        "error": result.get('data', {}).get('error', {}).get('message', ''),
                        "task_id": task_id
                    }
        
        return {"success": False, "error": "查询超时", "task_id": task_id}


class yuansora:
    """自定义API视频生成类"""
    
    def __init__(self):
        cfg = API_CONFIG["yuansora"]
        self.api_key = cfg["api_key"]
        self.api_host = cfg["api_host"]
        self.api_port = cfg["api_port"]
    
    def _upload_to_relay(self, file_path: str, file_type: str) -> str:
        """
        上传文件到中转服务器（与已跑通代码一致）
        file_type: 'image' 或 'video'
        返回: URL(成功) 或 原路径(失败)
        """
        try:
            server = API_CONFIG["upload_servers"][file_type]
            upload_url = f"{server}/upload/{file_type}"
            
            filename = Path(file_path).name
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            files = {
                file_type: (filename, file_data, 'video/mp4' if file_type == 'video' else 'image/jpeg')
            }
            
            response = requests.post(
                upload_url,
                files=files,
                headers={"ngrok-skip-browser-warning": "true"},
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                url = result.get('url') or result.get('data', {}).get('url')
                print(f"{file_type} 上传成功: {url}")
                return url
            else:
                print(f"{file_type} 上传失败 (HTTP {response.status_code}), 使用本地路径")
                return file_path
        except Exception as e:
            print(f"{file_type} 上传异常: {str(e)}, 使用本地路径")
            return file_path
    
    def generate(self, prompt: str, duration: int, orientation: str,
                 image_file_path: Optional[str] = None, watermark: bool = False) -> Dict:
        
        import http.client
        from codecs import encode
        import json
        
        size = "720x1280" if orientation == "portrait" else "1280x720"
        
        try:
            conn = http.client.HTTPConnection(self.api_host, self.api_port)
            boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
            dataList = []
            
            # model
            dataList.append(encode('--' + boundary))
            dataList.append(encode('Content-Disposition: form-data; name=model;'))
            dataList.append(encode('Content-Type: text/plain'))
            dataList.append(encode(''))
            dataList.append(encode('sora_video2'))
            
            # prompt
            dataList.append(encode('--' + boundary))
            dataList.append(encode('Content-Disposition: form-data; name=prompt;'))
            dataList.append(encode('Content-Type: text/plain'))
            dataList.append(encode(''))
            dataList.append(encode(prompt))
            
            # seconds
            dataList.append(encode('--' + boundary))
            dataList.append(encode('Content-Disposition: form-data; name=seconds;'))
            dataList.append(encode('Content-Type: text/plain'))
            dataList.append(encode(''))
            dataList.append(encode(str(duration)))
            
            # 图片（可选）
            if image_file_path:
                # 尝试上传到中转服务器
                processed_path = self._upload_to_relay(image_file_path, 'image')
                
                # 无论上传成功与否，都处理文件
                if processed_path.startswith('http'):
                    # 从URL下载
                    img_response = requests.get(processed_path)
                    file_data = img_response.content
                else:
                    # 从本地读取
                    with open(processed_path, 'rb') as f:
                        file_data = f.read()
                
                dataList.append(encode('--' + boundary))
                dataList.append(encode(f'Content-Disposition: form-data; name=input_reference; filename={Path(image_file_path).name}'))
                dataList.append(encode('Content-Type: image/jpeg'))
                dataList.append(encode(''))
                dataList.append(file_data)
            
            # size
            dataList.append(encode('--' + boundary))
            dataList.append(encode('Content-Disposition: form-data; name=size;'))
            dataList.append(encode('Content-Type: text/plain'))
            dataList.append(encode(''))
            dataList.append(encode(size))
            
            # watermark
            dataList.append(encode('--' + boundary))
            dataList.append(encode('Content-Disposition: form-data; name=watermark;'))
            dataList.append(encode('Content-Type: text/plain'))
            dataList.append(encode(''))
            dataList.append(encode(str(watermark).lower()))
            
            dataList.append(encode('--' + boundary + '--'))
            dataList.append(encode(''))
            
            body = b'\r\n'.join(dataList)
            headers = {
                'Authorization': self.api_key,
                'Content-type': f'multipart/form-data; boundary={boundary}'
            }
            
            conn.request("POST", "/v1/videos", body, headers)
            res = conn.getresponse()
            response_data = res.read()
            
            if res.status != 200:
                return {"success": False, "error": response_data.decode('utf-8'), "task_id": None}
            
            result = json.loads(response_data.decode('utf-8'))
            task_id = result.get("id")
            conn.close()
            
            # 轮询
            for _ in range(60):
                time.sleep(10)
                
                query_conn = http.client.HTTPConnection(self.api_host, self.api_port)
                query_headers = {
                    'Authorization': self.api_key,
                    'Content-Type': 'application/json'
                }
                
                query_conn.request("GET", f"/v1/videos/{task_id}", '', query_headers)
                query_res = query_conn.getresponse()
                query_data = query_res.read()
                
                if query_res.status == 200:
                    query_result = json.loads(query_data.decode('utf-8'))
                    status = query_result.get('status')
                    
                    if status == 'completed':
                        query_conn.close()
                        return {
                            "success": True,
                            "video_url": query_result.get('video_url', ''),
                            "task_id": task_id
                        }
                    elif status == 'failed':
                        query_conn.close()
                        return {
                            "success": False,
                            "error": query_result.get('error', {}).get('message', '生成失败'),
                            "task_id": task_id
                        }
                
                query_conn.close()
            
            return {"success": False, "error": "查询超时", "task_id": task_id}
        
        except Exception as e:
            return {"success": False, "error": str(e), "task_id": None}


class yunwujuese:
    """角色创建类"""
    
    def __init__(self):
        cfg = API_CONFIG["yunwujuese"]
        self.api_key = cfg["api_key"]
        self.base_url = cfg["base_url"]
    
    def _upload_to_relay(self, file_path: str, file_type: str) -> str:
        """
        上传文件到中转服务器（与已跑通代码一致）
        file_type: 'image' 或 'video'
        返回: URL(成功) 或 原路径(失败)
        """
        try:
            server = API_CONFIG["upload_servers"][file_type]
            upload_url = f"{server}/upload/{file_type}"
            
            filename = Path(file_path).name
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            files = {
                file_type: (filename, file_data, 'video/mp4' if file_type == 'video' else 'image/jpeg')
            }
            
            response = requests.post(
                upload_url,
                files=files,
                headers={"ngrok-skip-browser-warning": "true"},
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                url = result.get('url') or result.get('data', {}).get('url')
                print(f"{file_type} 上传成功: {url}")
                return url
            else:
                print(f"{file_type} 上传失败 (HTTP {response.status_code}), 使用本地路径")
                return file_path
        except Exception as e:
            print(f"{file_type} 上传异常: {str(e)}, 使用本地路径")
            return file_path
    
    def create(self, timestamps: str, url: Optional[str] = None, 
               from_task: Optional[str] = None) -> Dict:
        
        payload = {"timestamps": timestamps}
        
        if url:
            # 判断是否为本地路径
            if not url.startswith('http'):
                # 尝试上传到中转服务器
                url = self._upload_to_relay(url, 'video')
            
            payload["url"] = url
        elif from_task:
            payload["from_task"] = from_task
        else:
            return {"success": False, "error": "需要提供 url 或 from_task"}
        
        response = requests.post(
            f"{self.base_url}/sora/v1/characters",
            json=payload,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            },
            timeout=180
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "character_id": result.get('id'),
                "username": result.get('username')
            }
        else:
            return {"success": False, "error": response.text}