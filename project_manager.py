"""
工程管理器 - 最简洁版本
"""
import json
from pathlib import Path
from datetime import datetime


class ProjectManager:
    """工程数据管理 - 每次操作自动保存"""
    
    def __init__(self, projects_dir="projects"):
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(exist_ok=True)
    
    def create(self, theme):
        """创建新工程"""
        project_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        data = {
            "id": project_id,
            "theme": theme,
            "created_at": datetime.now().isoformat(),
            
            # Agent结果
            "script": "",
            "base_json": [],
            
            # 素材
            "characters": {},  # {js1: {prompt: "", base_img: "", view_img: ""}}
            "scenes": {},      # {scene1: {prompt: "", img: ""}}
            "segments": []     # [{id, time, edesc, videodesc, cap, js, local, img}]
        }
        
        self._save(data)
        return data
    
    def load(self, project_id):
        """加载工程"""
        filepath = self.projects_dir / f"{project_id}.json"
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save(self, data):
        """保存工程"""
        self._save(data)
    
    def _save(self, data):
        """内部保存方法"""
        filepath = self.projects_dir / f"{data['id']}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def list_projects(self):
        """列出所有工程"""
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
    
    def update_script(self, data, script):
        """更新文案"""
        data["script"] = script
        self._save(data)
        return data
    
    def update_segments(self, data, segments):
        """更新分镜"""
        data["segments"] = segments
        self._save(data)
        return data
    
    def update_character(self, data, char_id, updates):
        """更新人物数据"""
        if char_id not in data["characters"]:
            data["characters"][char_id] = {}
        data["characters"][char_id].update(updates)
        self._save(data)
        return data
    
    def update_scene(self, data, scene_id, updates):
        """更新场景数据"""
        if scene_id not in data["scenes"]:
            data["scenes"][scene_id] = {}
        data["scenes"][scene_id].update(updates)
        self._save(data)
        return data
    
    def update_segment_image(self, data, segment_id, img_path):
        """更新分镜图片"""
        for seg in data["segments"]:
            if seg["segment_id"] == segment_id:
                seg["img"] = img_path
                break
        self._save(data)
        return data