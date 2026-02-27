"""
AI动画剧情工程管理器 - 完整版 v2.0
✅ 一键生成所有素材
✅ 图生图支持(多角度图+场景图→分镜图)
✅ 模型选择
"""
import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI
import time
import requests
import uuid
from video_yunwu import VideoYunwuGenerator
from video_yuanai import VideoYuanaiGenerator
###继续加平台api和对应工具类


# ==================== 配置 ====================
DEEPSEEK_API_KEY = "sk-a2e28559994a4129bf6b2282ba034e6e"
GRSAI_API_KEY = "sk-ca999d825073499cbe1a0a724f91461c"
GRSAI_HOST = "https://grsai.dakka.com.cn"
IMAGE_UPLOAD_SERVER = "http://43.143.145.118:8085"  # 图片代理服务器
TIMEOUT = 300


# ==================== 图片上传中转 ====================
def upload_image_to_server(image_path):
    """上传图片到中转服务器获取URL"""
    try:
        upload_url = f"{IMAGE_UPLOAD_SERVER.rstrip('/')}/upload/image"
        
        # 智能检测文件类型
        ext = Path(image_path).suffix.lower()
        if ext == '.png':
            mime_type = 'image/png'
        elif ext in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        elif ext == '.gif':
            mime_type = 'image/gif'
        elif ext == '.webp':
            mime_type = 'image/webp'
        else:
            mime_type = 'image/png'
        
        with open(image_path, 'rb') as f:
            files = {'image': (Path(image_path).name, f, mime_type)}
            response = requests.post(
                upload_url,
                files=files,
                headers={"ngrok-skip-browser-warning": "true"},
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('url') or result.get('data', {}).get('url')
        else:
            raise Exception(f"上传失败: HTTP {response.status_code}")
    except Exception as e:
        raise Exception(f"图片上传失败: {e}")


# ==================== 图片生成API ====================
class ImageGenerator:
    """图片生成器(支持图生图)"""
    
    def __init__(self):
        self.api_key = GRSAI_API_KEY
        self.api_host = GRSAI_HOST
        self.timeout = TIMEOUT
    
    def generate_id(self):
        return str(uuid.uuid4())[:8]
    
    def download_image(self, image_url, save_path):
        """下载图片到指定路径"""
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()
        
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, "wb") as f:
            f.write(response.content)
        
        return save_path
    
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
            
            response = requests.post(
                f"{self.api_host}/v1/draw/result",
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
    
    def generate(self, prompt, model="sora-image", size="1:1", reference_urls=None, save_path=None, is_storyboard=False):
        """
        生成图片(支持图生图)
        
        Args:
            prompt: 提示词
            model: 模型名称
            size: 图片比例
            reference_urls: 参考图片URL列表(图生图)
            save_path: 保存路径
            is_storyboard: 是否为分镜图(只有分镜图才添加4宫格前缀)
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 只在分镜图时添加4宫格前缀
        if is_storyboard and reference_urls:
            storyboard_prefix = "[保持与上传图片完全一致的写实风格,生成四宫格故事画面,画面保持和原图一样的写实风格,呈现必须具备丰富而精彩的分镜与多样景别,包括但不限于:特写、远景、俯拍、仰拍、运动镜头等,以强化紧张感与画面表现力,禁止出现对话旁白。"
            prompt = f"{storyboard_prefix} {prompt}"
        
        # GPT模型 (sora-image, gpt-image-1.5)
        if model in ["sora-image", "gpt-image-1.5"]:
            payload = {
                "model": model,
                "prompt": prompt,
                "size": size,
                "variants": 1,
                "webHook": "-1",
                "shutProgress": False
            }
            
            # 添加参考图片
            if reference_urls:
                payload["urls"] = reference_urls
            
            endpoint = f"{self.api_host}/v1/draw/completions"
        
        # Banana模型
        elif "banana" in model:
            # Banana API不支持参考图片,改用GPT
            if reference_urls:
                st.warning("⚠️ Banana模型不支持图生图,自动切换到sora-image")
                return self.generate(prompt, "sora-image", size, reference_urls, save_path, is_storyboard)
            
            payload = {
                "model": model,
                "prompt": prompt,
                "aspectRatio": size,
                "imageSize": "2K",
                "webHook": "-1",
                "shutProgress": False
            }
            endpoint = f"{self.api_host}/v1/draw/nano-banana"
        
        else:
            raise ValueError(f"不支持的模型: {model}")
        
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
        
        data = self.poll_result(task_id)
        
        # 获取图片URL
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
            save_path = f"temp_{self.generate_id()}.png"
        
        return self.download_image(image_url, save_path)


# ==================== DeepSeek API (保持不变) ====================
class DeepSeekClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )
    
    def call(self, prompt, system_msg="你是一个专业的AI助手"):
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                stream=False
            )
            
            result = response.choices[0].message.content
            
            conversation = {
                "timestamp": datetime.now().isoformat(),
                "system": system_msg,
                "user": prompt,
                "assistant": result,
                "model": "deepseek-chat"
            }
            
            return result, conversation
            
        except Exception as e:
            error_msg = f"API调用错误: {str(e)}"
            conversation = {
                "timestamp": datetime.now().isoformat(),
                "system": system_msg,
                "user": prompt,
                "assistant": error_msg,
                "model": "deepseek-chat",
                "error": True
            }
            return error_msg, conversation


# ==================== 提示词解析器 ====================
def parse_character_scene_prompts(text):
    """解析Step4的人物场景提示词"""
    result = {"characters": {}, "scenes": {}}
    
    lines = text.split("\n")
    current_section = None
    current_char = None
    current_scene = None
    
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
        
        # 识别章节
        if "人物" in line or "Character" in line:
            current_section = "character"
            continue
        elif "场景" in line or "Scene" in line or "环境" in line:
            current_section = "scene"
            continue
        
        if current_section == "character":
            # 识别人物名称
            if line.endswith("：") or line.endswith(":"):
                current_char = line.rstrip("：:")
                result["characters"][current_char] = {"prompt": "", "base_img": "", "view_img": ""}
                continue
            
            # 识别提示词
            if current_char and (":" in line or "：" in line):
                # 支持多种格式: "people:", "提示词:", "prompt:", 或直接冒号
                if any(keyword in line.lower() for keyword in ["people", "prompt", "提示词"]):
                    prompt = line.split(":", 1)[-1].split("：", 1)[-1].strip().strip('"').strip("'")
                    if prompt:
                        result["characters"][current_char]["prompt"] = prompt
        
        elif current_section == "scene":
            # 识别场景名称
            if line.endswith("：") or line.endswith(":"):
                current_scene = line.rstrip("：:")
                result["scenes"][current_scene] = {"prompt": "", "img": ""}
                continue
            
            # 识别提示词
            if current_scene and (":" in line or "：" in line):
                # 支持多种格式: "local:", "提示词:", "prompt:", 或直接冒号
                if any(keyword in line.lower() for keyword in ["local", "prompt", "提示词", "场景"]):
                    prompt = line.split(":", 1)[-1].split("：", 1)[-1].strip().strip('"').strip("'")
                    if prompt:
                        result["scenes"][current_scene]["prompt"] = prompt
    
    return result


# ==================== 提示词模板 ====================
class PromptTemplates:
    
    @staticmethod
    def step1_template():
        return """你是一个专业的AI提示词扩写专家和视频内容策略顾问。
你的任务是根据用户提供的简短、核心关键词指令，自动扩写并生成一个完整、详细且专业的**"AI剧情性视频文案生成提示词"**。

[生成提示词模板开始]
你是一个专业的电影编剧、创意总监和科幻故事作家。
我需要你为一部短视频创作一个高度吸引人、充满剧情性和张力的视频文案。

视频核心要求：
主题： [根据用户指令中的主题进行填充和扩写]
时长： [根据用户指令中的时长进行填充]
主角： [根据用户指令中的主角进行填充]
配角： [根据用户指令中的配角进行填充]

剧情要素：
开端： 设定世界背景，引入危机
发展： 展现主角如何面对危机
高潮/抉择： 关键性的抉择
结局： 危机解决或新的篇章

请直接给我这段剧情性的视频文案，只需要一大段，无需任何前言或解释。
[生成提示词模板结束]

我的简短关键词指令是： {theme}"""

    @staticmethod
    def step3_template(script, theme):
        return f"""你是一个专业的视频脚本策划师、分镜设计师。
请根据以下视频文案生成JSON格式的分镜脚本。

JSON结构：
每个分镜包含：
- segment_id: 分镜ID
- time_range: 时间范围
- edesc: 图片生成提示词(英文,详细描述画面)
- videodesc: 视频生成提示词  
- cap: 分镜描述
- js: 出现的角色(用逗号分隔,如"js1,js2")
- local: 场景名称

只输出JSON数组，不要有其他文字。

视频文案：
{script}

主题：
{theme}"""

    @staticmethod
    def step4_template(base_json):
        return f"""你是一个专业的AI图像提示词专家。
请从以下分镜JSON中提取所有人物和场景，并生成英文生图提示词。

重要规则：
1. 场景名称必须从分镜JSON的"local"字段提取，不要自己编造
2. 每个不同的场景都要单独列出
3. local提示词要详细描述场景环境（不是室内名称）

输出格式（严格按照此格式）：
人物形象提示词：
js1：
people: "英文生图提示词,详细描述外貌、服装、气质"

js2：
people: "英文生图提示词,详细描述外貌、服装、气质"

场景环境提示词：
[从JSON的local字段提取的场景名]：
local: "英文生图提示词,详细描述场景的环境、光线、氛围、地形、建筑风格等"

[另一个场景名]：
local: "英文生图提示词..."

分镜JSON：
{base_json}"""

    @staticmethod
    def step5_template(base_json, character_scene):
        return f"""你是一位资深电影摄影师。
请整合分镜和人物场景信息，生成完整的分镜JSON。

输出格式：
标准JSON数组，每个分镜包含：
- segment_id, time_range, edesc(英文), videodesc, cap, js, local

只输出JSON数组。

原始分镜：
{base_json}

人物场景：
{character_scene}"""


# ==================== Agent ====================
class StoryAgent:
    def __init__(self):
        self.client = DeepSeekClient()
        self.prompts = PromptTemplates()
    
    def step1_generate_script_prompt(self, theme):
        prompt = self.prompts.step1_template().format(theme=theme)
        return self.client.call(prompt)
    
    def step2_generate_script(self, script_prompt):
        return self.client.call(script_prompt)
    
    def step3_generate_base_storyboard(self, script, theme):
        prompt = self.prompts.step3_template(script, theme)
        result, conversation = self.client.call(prompt)
        
        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            json_data = json.loads(cleaned)
            return json.dumps(json_data, ensure_ascii=False, indent=2), conversation
        except:
            return result, conversation
    
    def step4_extract_characters_scenes(self, base_json):
        prompt = self.prompts.step4_template(base_json)
        result, conversation = self.client.call(prompt)
        
        parsed = parse_character_scene_prompts(result)
        
        return result, conversation, parsed
    
    def step5_generate_final_storyboard(self, base_json, character_scene):
        prompt = self.prompts.step5_template(base_json, character_scene)
        result, conversation = self.client.call(prompt)
        
        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            json_data = json.loads(cleaned)
            return json_data, conversation
        except:
            return result, conversation


# ==================== 工程管理器 ====================
class ProjectManager:
    def __init__(self, projects_dir="projects"):
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(exist_ok=True)
    
    def create(self, theme):
        project_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        data = {
            "id": project_id,
            "theme": theme,
            "created_at": datetime.now().isoformat(),
            
            "script": "",
            "base_json": [],
            
            "characters": {},
            "scenes": {},
            "segments": [],
            
            "conversations": [],
            
            # 一键生成设置
            "one_click_settings": {
                "model": "sora-image",
                "character_size": "1:1",
                "scene_size": "16:9",
                "storyboard_size": "16:9"
            }
        }
        
        self._save(data)
        return data
    
    def load(self, project_id):
        filepath = self.projects_dir / f"{project_id}.json"
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "one_click_settings" not in data:
                data["one_click_settings"] = {
                    "model": "sora-image",
                    "character_size": "1:1",
                    "scene_size": "16:9",
                    "storyboard_size": "16:9"
                }
            return data
    
    def save(self, data):
        self._save(data)
    
    def _save(self, data):
        filepath = self.projects_dir / f"{data['id']}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def list_projects(self):
        projects = []
        for file in self.projects_dir.glob("*.json"):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                projects.append({
                    "id": data["id"],
                    "theme": data.get("theme", "未命名"),
                    "created_at": data.get("created_at", "")
                })
        return sorted(projects, key=lambda x: x["created_at"], reverse=True)
    
    def add_conversation(self, data, conversation):
        if "conversations" not in data:
            data["conversations"] = []
        data["conversations"].append(conversation)
        self._save(data)
        return data
    
    def update_script(self, data, script):
        data["script"] = script
        self._save(data)
        return data
    
    def update_segments(self, data, segments):
        data["segments"] = segments
        self._save(data)
        return data
    
    def update_characters_batch(self, data, characters_dict):
        for char_id, char_data in characters_dict.items():
            if char_id not in data["characters"]:
                data["characters"][char_id] = {}
            data["characters"][char_id].update(char_data)
        self._save(data)
        return data
    
    def update_scenes_batch(self, data, scenes_dict):
        for scene_id, scene_data in scenes_dict.items():
            if scene_id not in data["scenes"]:
                data["scenes"][scene_id] = {}
            data["scenes"][scene_id].update(scene_data)
        self._save(data)
        return data
    
    def update_character(self, data, char_id, updates):
        if char_id not in data["characters"]:
            data["characters"][char_id] = {}
        data["characters"][char_id].update(updates)
        self._save(data)
        return data
    
    def update_scene(self, data, scene_id, updates):
        if scene_id not in data["scenes"]:
            data["scenes"][scene_id] = {}
        data["scenes"][scene_id].update(updates)
        self._save(data)
        return data
    
    def update_segment_image(self, data, segment_id, img_path):
        for seg in data["segments"]:
            if seg["segment_id"] == segment_id:
                seg["img"] = img_path
                break
        self._save(data)
        return data
    
    def update_segment_video(self, data, segment_id, video_path):
        """更新分镜视频路径"""
        for seg in data["segments"]:
            if seg["segment_id"] == segment_id:
                seg["video"] = video_path
                break
        self._save(data)
        return data
    
    def update_one_click_settings(self, data, settings):
        """更新一键生成设置"""
        data["one_click_settings"].update(settings)
        self._save(data)
        return data


# ==================== 辅助函数 ====================
def extract_characters_from_segments(segments):
    chars = set()
    for seg in segments:
        if seg.get("js"):
            chars.update(seg["js"].split(","))
    return sorted(chars)

def extract_scenes_from_segments(segments):
    scenes = set()
    for seg in segments:
        if seg.get("local"):
            scenes.add(seg["local"])
    return sorted(scenes)

def generate_video_with_fallback(image_url, prompt, duration, save_path):##参数可变
    """
    多平台视频生成（自动切换）
    
    如果当前平台失败，自动切换到下一个平台重试
    
    Args:
        image_url: 参考图片URL
        prompt: 视频生成提示词
        duration: 视频时长(秒)
        save_path: 保存路径
    
    Returns:
        tuple: (视频文件路径, 使用的平台名称)
    
    Raises:
        Exception: 所有平台都失败时抛出异常
    """
    # 定义所有可用的视频生成器平台
    generators = [
        ("云雾", VideoYunwuGenerator),
        ("源AI", VideoYuanaiGenerator),
        # ("平台3", VideoPlatform3Generator),
    ]
    
    last_error = None
    
    for platform_name, GeneratorClass in generators:
        try:
            st.info(f"🔄 尝试使用 {platform_name} 平台生成视频...")
            
            # 创建生成器实例
            generator = GeneratorClass()
            
            # 尝试生成视频
            video_path = generator.generate(
                image_url=image_url,
                prompt=prompt,
                duration=duration,
                save_path=save_path
            )
            
            # 成功则返回
            st.success(f"✅ 使用 {platform_name} 平台生成成功！")
            return video_path, platform_name
            
        except Exception as e:
            # 记录错误，继续尝试下一个平台
            last_error = e
            st.warning(f"⚠️ {platform_name} 平台失败: {str(e)}")
            st.info(f"🔄 自动切换到下一个平台...")
            continue
    
    # 所有平台都失败
    error_msg = f"❌ 所有平台都失败了。最后一个错误: {str(last_error)}"
    raise Exception(error_msg)


# ==================== 一键生成函数 ====================
def one_click_generate_assets(proj, pm, img_gen, mode="simple"):
    """
    一键生成所有素材 - 只生成未生成的
    
    Args:
        proj: 工程数据
        pm: 工程管理器
        img_gen: 图片生成器
        mode: "simple" = 仅生成人物+场景
              "advanced" = 人物+场景+分镜(图生图)
    """
    settings = proj.get("one_click_settings", {})
    model = settings.get("model", "sora-image")
    char_size = settings.get("character_size", "1:1")
    scene_size = settings.get("scene_size", "16:9")
    story_size = settings.get("storyboard_size", "16:9")
    
    characters = extract_characters_from_segments(proj["segments"])
    scenes = extract_scenes_from_segments(proj["segments"])
    
    # 统计需要生成的素材
    todo_base = sum(1 for c in characters if not proj["characters"].get(c, {}).get("base_img"))
    todo_view = sum(1 for c in characters if not proj["characters"].get(c, {}).get("view_img"))
    todo_scene = sum(1 for s in scenes if not proj["scenes"].get(s, {}).get("img"))
    todo_segment = sum(1 for seg in proj["segments"] if not seg.get("img")) if mode == "advanced" else 0
    
    total_steps = todo_base + todo_view + todo_scene + todo_segment
    
    if total_steps == 0:
        return proj, True, "✅ 所有素材已生成"
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    current_step = 0
    
    try:
        # 1. 生成人物基础图
        for char_id in characters:
            char = proj["characters"].get(char_id, {})
            if char.get("base_img"):
                continue  # 跳过已生成
            
            prompt = char.get("prompt", "")
            if not prompt:
                st.warning(f"⚠️ {char_id} 没有提示词,跳过")
                continue
            
            status_text.info(f"🎨 生成 {char_id} 基础图...")
            save_path = f"images/{proj['id']}/characters/{char_id}_base.png"
            img_path = img_gen.generate(prompt, model, char_size, None, save_path)
            proj = pm.update_character(proj, char_id, {"base_img": img_path})
            
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        
        # 2. 生成人物多角度图
        for char_id in characters:
            char = proj["characters"].get(char_id, {})
            if char.get("view_img"):
                continue  # 跳过已生成
            
            prompt = char.get("prompt", "")
            base_img = char.get("base_img", "")
            if not prompt or not base_img:
                continue
            
            status_text.info(f"🔄 生成 {char_id} 多角度图...")
            view_prompt = f"{prompt}, character turnaround, front view, back view, side view, white background, character sheet"
            save_path = f"images/{proj['id']}/characters/{char_id}_views.png"
            
            # 上传基础图作为参考
            base_url = upload_image_to_server(base_img)
            img_path = img_gen.generate(view_prompt, model, "16:9", [base_url], save_path)
            
            proj = pm.update_character(proj, char_id, {"view_img": img_path})
            
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        
        # 3. 生成场景图
        for scene_id in scenes:
            scene = proj["scenes"].get(scene_id, {})
            if scene.get("img"):
                continue  # 跳过已生成
            
            prompt = scene.get("prompt", "")
            if not prompt:
                st.warning(f"⚠️ {scene_id} 没有提示词,跳过")
                continue
            
            status_text.info(f"🏞️ 生成场景 {scene_id}...")
            save_path = f"images/{proj['id']}/scenes/{scene_id}.png"
            img_path = img_gen.generate(prompt, model, scene_size, None, save_path)
            proj = pm.update_scene(proj, scene_id, {"img": img_path})
            
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        
        # 4. 高级模式：生成分镜图(图生图)
        if mode == "advanced":
            for seg in proj["segments"]:
                if seg.get("img"):
                    continue  # 跳过已生成
                
                seg_id = seg["segment_id"]
                edesc = seg.get("edesc", "")
                cap = seg.get("cap", "")
                js_ids = seg.get("js", "").split(",")
                scene_id = seg.get("local", "")
                
                if not edesc:
                    continue
                
                status_text.info(f"🎬 生成分镜 {seg_id}...")
                
                reference_urls = []
                
                # 收集人物多角度图
                for js_id in js_ids:
                    char = proj["characters"].get(js_id, {})
                    view_img = char.get("view_img", "")
                    if view_img and Path(view_img).exists():
                        url = upload_image_to_server(view_img)
                        reference_urls.append(url)
                
                # 收集场景图
                scene = proj["scenes"].get(scene_id, {})
                scene_img = scene.get("img", "")
                if scene_img and Path(scene_img).exists():
                    url = upload_image_to_server(scene_img)
                    reference_urls.append(url)
                
                # 4宫格提示词前缀（中文）
                save_path = f"images/{proj['id']}/storyboard/segment_{seg_id}.png"
                
                # 图生图生成分镜（自动添加4宫格前缀）
                img_path = img_gen.generate(edesc, model, story_size, reference_urls, save_path, is_storyboard=True)
                proj = pm.update_segment_image(proj, seg_id, img_path)
                
                current_step += 1
                progress_bar.progress(current_step / total_steps)
        
        status_text.success(f"✅ 一键生成完成！")
        progress_bar.progress(1.0)
        
        return proj, True, "✅ 一键生成完成"
    
    except Exception as e:
        status_text.error(f"❌ 生成失败: {e}")
        return proj, False, f"❌ {e}"


# ==================== Streamlit UI ====================
st.set_page_config(
    page_title="AI动画工程管理器",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化
if 'pm' not in st.session_state:
    st.session_state.pm = ProjectManager()

if 'agent' not in st.session_state:
    st.session_state.agent = StoryAgent()

if 'img_gen' not in st.session_state:
    st.session_state.img_gen = ImageGenerator()

if 'current_project' not in st.session_state:
    st.session_state.current_project = None

if 'show_conversations' not in st.session_state:
    st.session_state.show_conversations = False


# ==================== 侧边栏 ====================
with st.sidebar:
    st.header("📂 工程管理")
    
    with st.expander("➕ 新建工程", expanded=False):
        new_theme = st.text_input(
            "主题",
            placeholder="未来主题，主角女，配角1个男，15s",
            key="new_theme"
        )
        if st.button("创建", key="create_btn"):
            if new_theme:
                project = st.session_state.pm.create(new_theme)
                st.session_state.current_project = project
                st.success(f"✅ 已创建: {project['id']}")
                st.rerun()
    
    st.subheader("📋 已有工程")
    projects = st.session_state.pm.list_projects()
    
    if projects:
        for proj in projects:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(f"{proj['theme'][:20]}...")
            with col2:
                if st.button("打开", key=f"open_{proj['id']}"):
                    st.session_state.current_project = st.session_state.pm.load(proj['id'])
                    st.rerun()
    else:
        st.info("暂无工程")
    
    if st.session_state.current_project:
        st.divider()
        st.success(f"📂 {st.session_state.current_project['id']}")
        
        if st.button("💬 查看对话记录", key="show_conv_btn"):
            st.session_state.show_conversations = True
            st.rerun()
        
        if st.button("💾 保存", key="manual_save"):
            st.session_state.pm.save(st.session_state.current_project)
            st.success("已保存")


# ==================== 对话记录界面 ====================
if st.session_state.show_conversations:
    st.title("💬 大模型对话记录")
    
    if st.button("← 返回主界面"):
        st.session_state.show_conversations = False
        st.rerun()
    
    proj = st.session_state.current_project
    
    if not proj:
        st.warning("请先选择工程")
        st.stop()
    
    st.info(f"工程: {proj['id']} | 主题: {proj['theme']}")
    
    conversations = proj.get("conversations", [])
    
    if not conversations:
        st.warning("暂无对话记录")
    else:
        st.metric("对话总数", len(conversations))
        
        for idx, conv in enumerate(reversed(conversations), 1):
            with st.expander(
                f"对话 {len(conversations) - idx + 1} | {conv.get('timestamp', '')[:19]}",
                expanded=(idx == 1)
            ):
                st.markdown("**🤖 System:**")
                st.code(conv.get('system', ''), language='text')
                
                st.markdown("**👤 User:**")
                user_msg = conv.get('user', '')
                if len(user_msg) > 500:
                    st.text_area("", value=user_msg, height=200, disabled=True, key=f"user_{idx}")
                else:
                    st.code(user_msg, language='text')
                
                st.markdown("**🤖 Assistant:**")
                assistant_msg = conv.get('assistant', '')
                
                if conv.get('error'):
                    st.error(assistant_msg)
                else:
                    if len(assistant_msg) > 500:
                        st.text_area("", value=assistant_msg, height=300, disabled=True, key=f"assistant_{idx}")
                    else:
                        st.code(assistant_msg, language='text')
                
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"模型: {conv.get('model', 'N/A')}")
                with col2:
                    st.caption(f"时间: {conv.get('timestamp', 'N/A')[:19]}")
    
    st.stop()


# ==================== 主界面 ====================
if not st.session_state.current_project:
    st.title("🎬 AI动画剧情工程管理器")
    st.info("👈 请在左侧创建或打开工程")
    st.stop()

proj = st.session_state.current_project

st.title("🎬 AI动画剧情工程管理器 v2.0")

tab1, tab2, tab3, tab4 = st.tabs(["📝 剧本生成", "🎯 一键生成", "📊 素材管理", "⚙️ 设置"])


# ==================== Tab1: 剧本生成 ====================
with tab1:
    st.subheader("📝 剧本生成")
    
    st.text_input("主题", value=proj['theme'], disabled=True, key="theme_display")
    
    if st.button("🚀 生成剧本", type="primary"):
        
        with st.status("生成中...", expanded=True) as status:
            st.write("⏳ Step 1: 生成文案提示词...")
            step1, conv1 = st.session_state.agent.step1_generate_script_prompt(proj['theme'])
            proj = st.session_state.pm.add_conversation(proj, conv1)
            
            st.write("⏳ Step 2: 生成文案...")
            step2, conv2 = st.session_state.agent.step2_generate_script(step1)
            proj = st.session_state.pm.update_script(proj, step2)
            proj = st.session_state.pm.add_conversation(proj, conv2)
            
            st.write("⏳ Step 3: 生成基础分镜...")
            step3, conv3 = st.session_state.agent.step3_generate_base_storyboard(step2, proj['theme'])
            proj = st.session_state.pm.add_conversation(proj, conv3)
            
            st.write("⏳ Step 4: 提取人物场景...")
            step4, conv4, parsed = st.session_state.agent.step4_extract_characters_scenes(step3)
            proj = st.session_state.pm.add_conversation(proj, conv4)
            
            if parsed["characters"]:
                proj = st.session_state.pm.update_characters_batch(proj, parsed["characters"])
            if parsed["scenes"]:
                proj = st.session_state.pm.update_scenes_batch(proj, parsed["scenes"])
            
            st.write("⏳ Step 5: 生成完整分镜...")
            step5, conv5 = st.session_state.agent.step5_generate_final_storyboard(step3, step4)
            proj = st.session_state.pm.add_conversation(proj, conv5)
            
            if isinstance(step5, list):
                proj = st.session_state.pm.update_segments(proj, step5)
                st.session_state.current_project = proj
                
                status.update(label="✅ 生成完成！", state="complete")
        
        # 调试信息放在status外面
        with st.expander("🔍 Step4解析结果（调试）", expanded=False):
            st.markdown("**原始输出:**")
            st.text_area("", value=step4, height=200, key="debug_step4", disabled=True)
            st.markdown("**解析后:**")
            st.json(parsed)
        
        st.success("✅ 人物和场景提示词已自动提取并保存")
        st.rerun()
    
    if proj.get("script"):
        st.text_area("📖 文案", value=proj["script"], height=150, disabled=True)
    
    if proj.get("segments"):
        st.divider()
        st.subheader(f"📺 分镜预览 ({len(proj['segments'])}个)")
        
        for seg in proj["segments"]:
            with st.expander(f"🎬 分镜 {seg['segment_id']} | {seg.get('time_range', '')}"):
                st.write(f"**Cap:** {seg.get('cap', '')}")
                st.write(f"**角色:** {seg.get('js', '')}")
                st.write(f"**场景:** {seg.get('local', '')}")


# ==================== Tab2: 一键生成 ====================
with tab2:
    st.subheader("🎯 一键生成所有素材")
    
    if not proj.get("segments"):
        st.warning("⚠️ 请先生成剧本")
    else:
        settings = proj.get("one_click_settings", {})
        
        st.info("💡 配置统一的生成参数,然后一键生成所有素材")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            model = st.selectbox(
                "统一模型",
                ["sora-image", "gpt-image-1.5", "nano-banana-fast", "nano-banana-pro"],
                index=0,
                key="one_click_model"
            )
        
        with col2:
            char_size = st.selectbox(
                "人物比例",
                ["1:1", "2:3", "3:4"],
                index=0,
                key="one_click_char_size"
            )
        
        with col3:
            scene_size = st.selectbox(
                "场景比例",
                ["16:9", "3:2", "1:1"],
                index=0,
                key="one_click_scene_size"
            )
        
        with col4:
            story_size = st.selectbox(
                "分镜比例",
                ["16:9", "9:16", "1:1"],
                index=0,
                key="one_click_story_size"
            )
        
        # 保存设置
        if st.button("💾 保存设置"):
            new_settings = {
                "model": model,
                "character_size": char_size,
                "scene_size": scene_size,
                "storyboard_size": story_size
            }
            proj = st.session_state.pm.update_one_click_settings(proj, new_settings)
            st.session_state.current_project = proj
            st.success("✅ 设置已保存")
        
        st.divider()
        
        # 生成按钮
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 模式1: 基础素材")
            st.caption("生成: 人物基础图 + 人物多角度图 + 场景图")
            
            if st.button("🎨 一键生成基础素材", type="primary", key="btn_simple", disabled=st.session_state.get('generating', False)):
                st.session_state.generating = True
                proj, success, msg = one_click_generate_assets(
                    proj,
                    st.session_state.pm,
                    st.session_state.img_gen,
                    mode="simple"
                )
                st.session_state.current_project = proj
                st.session_state.generating = False
                
                if success:
                    st.balloons()
                    st.rerun()
        
        with col2:
            st.markdown("### 模式2: 完整素材")
            st.caption("生成: 基础素材 + 分镜图(图生图)")
            
            if st.button("🚀 一键生成完整素材", type="primary", key="btn_advanced", disabled=st.session_state.get('generating', False)):
                st.session_state.generating = True
                proj, success, msg = one_click_generate_assets(
                    proj,
                    st.session_state.pm,
                    st.session_state.img_gen,
                    mode="advanced"
                )
                st.session_state.current_project = proj
                st.session_state.generating = False
                
                if success:
                    st.balloons()
                    st.rerun()


# ==================== Tab3: 素材管理 ====================
with tab3:
    st.subheader("📊 素材管理")
    
    if not proj.get("segments"):
        st.warning("⚠️ 请先生成剧本")
    else:
        sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["👤 人物", "🏞️ 场景", "🎬 分镜", "✂️ 剪辑"])
        
        # 人物管理
        with sub_tab1:
            characters = extract_characters_from_segments(proj["segments"])
            
            if characters:
                cols = st.columns(min(len(characters), 3))
                
                for idx, char_id in enumerate(characters):
                    with cols[idx % 3]:
                        st.markdown(f"### {char_id}")
                        
                        char = proj["characters"].get(char_id, {})
                        
                        # 编辑提示词
                        new_prompt = st.text_area(
                            "提示词",
                            value=char.get("prompt", ""),
                            height=80,
                            key=f"char_edit_{char_id}"
                        )
                        
                        if new_prompt != char.get("prompt", ""):
                            proj["characters"][char_id]["prompt"] = new_prompt
                            proj = st.session_state.pm.update_character(proj, char_id, {"prompt": new_prompt})
                            st.session_state.current_project = proj
                        
                        # 显示图片
                        if char.get("base_img") and Path(char["base_img"]).exists():
                            st.image(char["base_img"], caption="基础图", use_column_width=True)
                        
                        if char.get("view_img") and Path(char["view_img"]).exists():
                            st.image(char["view_img"], caption="多角度图", use_column_width=True)
                        
                        # 单独重新生成按钮
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🔄 重生基础图", key=f"regen_base_{char_id}"):
                                if new_prompt:
                                    try:
                                        with st.spinner("生成中..."):
                                            settings = proj.get("one_click_settings", {})
                                            model = settings.get("model", "sora-image")
                                            size = settings.get("character_size", "1:1")
                                            save_path = f"images/{proj['id']}/characters/{char_id}_base.png"
                                            img_path = st.session_state.img_gen.generate(new_prompt, model, size, None, save_path)
                                            proj = st.session_state.pm.update_character(proj, char_id, {"base_img": img_path})
                                            st.session_state.current_project = proj
                                            st.success("✅ 已重新生成")
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ {e}")
                        
                        with col2:
                            if char.get("base_img") and st.button("🔄 重生多角度", key=f"regen_view_{char_id}"):
                                try:
                                    with st.spinner("生成中..."):
                                        settings = proj.get("one_click_settings", {})
                                        model = settings.get("model", "sora-image")
                                        view_prompt = f"{new_prompt}, character turnaround, front view, back view, side view, white background, character sheet"
                                        save_path = f"images/{proj['id']}/characters/{char_id}_views.png"
                                        
                                        # 上传基础图作为参考
                                        base_url = upload_image_to_server(char["base_img"])
                                        img_path = st.session_state.img_gen.generate(view_prompt, model, "16:9", [base_url], save_path)
                                        
                                        proj = st.session_state.pm.update_character(proj, char_id, {"view_img": img_path})
                                        st.session_state.current_project = proj
                                        st.success("✅ 已重新生成")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"❌ {e}")
        
        # 场景管理
        with sub_tab2:
            scenes = extract_scenes_from_segments(proj["segments"])
            
            if scenes:
                cols = st.columns(min(len(scenes), 3))
                
                for idx, scene_id in enumerate(scenes):
                    with cols[idx % 3]:
                        st.markdown(f"### {scene_id}")
                        
                        scene = proj["scenes"].get(scene_id, {})
                        
                        # 编辑提示词
                        new_prompt = st.text_area(
                            "提示词",
                            value=scene.get("prompt", ""),
                            height=80,
                            key=f"scene_edit_{scene_id}"
                        )
                        
                        if new_prompt != scene.get("prompt", ""):
                            proj["scenes"][scene_id]["prompt"] = new_prompt
                            proj = st.session_state.pm.update_scene(proj, scene_id, {"prompt": new_prompt})
                            st.session_state.current_project = proj
                        
                        # 显示图片
                        if scene.get("img") and Path(scene["img"]).exists():
                            st.image(scene["img"], caption="场景图", use_column_width=True)
                        
                        # 单独重新生成按钮
                        if st.button("🔄 重新生成", key=f"regen_scene_{scene_id}"):
                            if new_prompt:
                                try:
                                    with st.spinner("生成中..."):
                                        settings = proj.get("one_click_settings", {})
                                        model = settings.get("model", "sora-image")
                                        size = settings.get("scene_size", "16:9")
                                        save_path = f"images/{proj['id']}/scenes/{scene_id}.png"
                                        img_path = st.session_state.img_gen.generate(new_prompt, model, size, None, save_path)
                                        proj = st.session_state.pm.update_scene(proj, scene_id, {"img": img_path})
                                        st.session_state.current_project = proj
                                        st.success("✅ 已重新生成")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"❌ {e}")
        
        # 分镜管理
        with sub_tab3:
            num_cols = 3
            for i in range(0, len(proj["segments"]), num_cols):
                cols = st.columns(num_cols)
                
                for j in range(num_cols):
                    idx = i + j
                    if idx < len(proj["segments"]):
                        seg = proj["segments"][idx]
                        
                        with cols[j]:
                            st.markdown(f"### 分镜 {seg['segment_id']}")
                            st.caption(seg.get('time_range', ''))
                            
                            # 显示图片
                            if seg.get("img") and Path(seg["img"]).exists():
                                st.image(seg["img"], use_column_width=True)
                            else:
                                st.info("未生成")
                            
                            # 编辑提示词
                            new_edesc = st.text_area(
                                "edesc",
                                value=seg.get("edesc", ""),
                                height=80,
                                key=f"seg_edit_{seg['segment_id']}"
                            )
                            
                            if new_edesc != seg.get("edesc", ""):
                                proj["segments"][idx]["edesc"] = new_edesc
                                proj = st.session_state.pm.update_segments(proj, proj["segments"])
                                st.session_state.current_project = proj
                            
                            # 单独重新生成按钮
                            if st.button("🔄 重新生成", key=f"regen_seg_{seg['segment_id']}"):
                                try:
                                    with st.spinner("生成中..."):
                                        settings = proj.get("one_click_settings", {})
                                        model = settings.get("model", "sora-image")
                                        size = settings.get("storyboard_size", "16:9")
                                        
                                        # 收集参考图
                                        reference_urls = []
                                        js_ids = seg.get("js", "").split(",")
                                        scene_id = seg.get("local", "")
                                        
                                        for js_id in js_ids:
                                            char = proj["characters"].get(js_id, {})
                                            view_img = char.get("view_img", "")
                                            if view_img and Path(view_img).exists():
                                                url = upload_image_to_server(view_img)
                                                reference_urls.append(url)
                                        
                                        scene = proj["scenes"].get(scene_id, {})
                                        scene_img = scene.get("img", "")
                                        if scene_img and Path(scene_img).exists():
                                            url = upload_image_to_server(scene_img)
                                            reference_urls.append(url)
                                        
                                        save_path = f"images/{proj['id']}/storyboard/segment_{seg['segment_id']}.png"
                                        
                                        # 图生图生成分镜（自动添加4宫格前缀）
                                        img_path = st.session_state.img_gen.generate(new_edesc, model, size, reference_urls, save_path, is_storyboard=True)
                                        
                                        proj = st.session_state.pm.update_segment_image(proj, seg["segment_id"], img_path)
                                        st.session_state.current_project = proj
                                        st.success("✅ 已重新生成")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"❌ {e}")
                            
                            # videodesc文本框（可编辑）
                            new_videodesc = st.text_area(
                                "videodesc",
                                value=seg.get("videodesc", ""),
                                height=80,
                                key=f"videodesc_{seg['segment_id']}"
                            )
                            
                            # 自动保存videodesc
                            if new_videodesc != seg.get("videodesc", ""):
                                proj["segments"][idx]["videodesc"] = new_videodesc
                                proj = st.session_state.pm.update_segments(proj, proj["segments"])
                                st.session_state.current_project = proj
                            
                            # 显示已生成的视频（如果存在）
                            if seg.get("video") and Path(seg["video"]).exists():
                                st.markdown("**已生成视频：**")
                                st.video(seg["video"])
                            
                            # 生成视频按钮
                            if st.button("🎬 生成视频", key=f"gen_video_seg_{seg['segment_id']}", type="primary"):
                                # 检查必要条件
                                if not seg.get("img") or not Path(seg["img"]).exists():
                                    st.error("❌ 请先生成分镜图")
                                elif not new_videodesc:
                                    st.error("❌ 请填写videodesc提示词")
                                else:
                                    try:
                                        with st.spinner("视频生成中，请耐心等待..."):
                                            # 上传分镜图到服务器
                                            img_url = upload_image_to_server(seg["img"])
                                            
                                            # 计算视频时长（从time_range中提取）
                                            time_range = seg.get("time_range", "0s-5s")
                                            try:
                                                if "-" in time_range:
                                                    end_time = time_range.split("-")[1].replace("s", "")
                                                    duration = int(end_time)
                                                else:
                                                    duration = 5
                                            except:
                                                duration = 5
                                            
                                            # 使用多平台自动切换生成视频
                                            save_path = f"images/{proj['id']}/videos/segment_{seg['segment_id']}.mp4"
                                            
                                            video_path, platform_name = generate_video_with_fallback(
                                                ###参数
                                                image_url=img_url,
                                                prompt=new_videodesc,
                                                duration=duration,
                                                save_path=save_path
                                            )
                                            
                                            # 更新工程数据
                                            proj = st.session_state.pm.update_segment_video(proj, seg["segment_id"], video_path)
                                            st.session_state.current_project = proj
                                            
                                            st.success(f"✅ 视频生成成功！(使用平台: {platform_name})")
                                            st.rerun()
                                    
                                    except Exception as e:
                                        st.error(f"❌ 视频生成失败: {e}")
                                        st.code(str(e))
        
        # 剪辑管理
        with sub_tab4:
            st.subheader("✂️ 视频剪辑")
            st.info("💡 视频剪辑功能")
            
            if not proj.get("segments"):
                st.warning("⚠️ 请先生成剧本和视频")
            else:
                # 检查是否有已生成的视频
                videos = []
                for seg in proj["segments"]:
                    if seg.get("video") and Path(seg["video"]).exists():
                        videos.append(seg)
                
                if not videos:
                    st.warning("⚠️ 请先生成视频")
                else:
                    st.success(f"✅ 已生成 {len(videos)} 个视频片段")
                    
                    # 显示所有视频片段
                    st.markdown("### 📹 视频片段列表")
                    for seg in videos:
                        with st.expander(f"分镜 {seg['segment_id']} - {seg.get('time_range', '')}"):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.video(seg["video"])
                                st.caption(f"提示词: {seg.get('videodesc', '')}")
                            
                            with col2:
                                st.markdown(f"**分镜ID:** {seg['segment_id']}")
                                st.markdown(f"**时间范围:** {seg.get('time_range', '')}")
                                
                                # 下载按钮
                                if Path(seg["video"]).exists():
                                    with open(seg["video"], "rb") as video_file:
                                        st.download_button(
                                            label="📥 下载视频",
                                            data=video_file,
                                            file_name=f"segment_{seg['segment_id']}.mp4",
                                            mime="video/mp4",
                                            key=f"download_clip_{seg['segment_id']}"
                                        )
                    
                    st.divider()
                    
                    # 剪辑功能区域
                    st.markdown("### 🎬 剪辑操作")
                    st.info("💡 剪辑功能开发中...")


# ==================== Tab4: 设置 ====================
with tab4:
    st.subheader("⚙️ 系统设置")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🔑 API配置")
        
        st.text_input("DeepSeek API Key", value=DEEPSEEK_API_KEY[:20] + "...", type="password", disabled=True)
        st.text_input("GrsAI API Key", value=GRSAI_API_KEY[:20] + "...", type="password", disabled=True)
        st.text_input("GrsAI Host", value=GRSAI_HOST, disabled=True)
        st.text_input("图片上传服务器", value=IMAGE_UPLOAD_SERVER, disabled=True)
        
        st.info("💡 如需修改API配置,请直接编辑 app_final_v2.py 文件顶部的配置项")
    
    with col2:
        st.markdown("### 📥 导出工程")
        
        st.download_button(
            label="📥 下载工程JSON",
            data=json.dumps(proj, ensure_ascii=False, indent=2),
            file_name=f"{proj['id']}.json",
            mime="application/json",
            use_container_width=True
        )
        
        conv_count = len(proj.get("conversations", []))
        st.metric("对话记录", f"{conv_count}条")


# ==================== 底部状态栏 ====================
st.divider()
col1, col2, col3, col4 = st.columns(4)

with col1:
    chars = extract_characters_from_segments(proj.get("segments", []))
    st.metric("人物", len(chars))

with col2:
    scenes = extract_scenes_from_segments(proj.get("segments", []))
    st.metric("场景", len(scenes))

with col3:
    st.metric("分镜", len(proj.get("segments", [])))

with col4:
    conv_count = len(proj.get("conversations", []))
    st.metric("对话", conv_count)