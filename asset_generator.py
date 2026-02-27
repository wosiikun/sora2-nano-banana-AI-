"""
素材生成器 - 调用image_generator
"""
from pathlib import Path


class AssetGenerator:
    """素材生成 - 生成后自动更新到工程JSON"""
    
    def __init__(self, image_gen_module):
        """
        image_gen_module: 你的image_generator模块
        """
        self.gen = image_gen_module
    
    def generate_character_base(self, project_id, char_id, prompt):
        """生成人物基础图"""
        print(f"\n🎨 生成人物图: {char_id}")
        
        img_path = self.gen.generate_image(
            prompt=prompt,
            model="nano-banana-fast",
            aspect_ratio="1:1",
            image_size="1K"
        )
        
        # 移动到工程目录
        new_path = self._move_to_project(project_id, img_path, f"characters/{char_id}_base.png")
        
        return new_path
    
    def generate_character_views(self, project_id, char_id, base_img_path):
        """生成人物多角度图 (图生图)"""
        print(f"\n🎨 生成多角度图: {char_id}")
        
        # TODO: 需要扩展image_generator支持图生图
        # 暂时用纯提示词生成
        prompt = f"白底，正面背面侧边，三视图，角色转换表，纯净背景"
        
        img_path = self.gen.generate_image(
            prompt=prompt,
            model="nano-banana-fast",
            aspect_ratio="16:9",
            image_size="1K"
        )
        
        new_path = self._move_to_project(project_id, img_path, f"characters/{char_id}_views.png")
        
        return new_path
    
    def generate_scene(self, project_id, scene_id, prompt):
        """生成场景图"""
        print(f"\n🏞️ 生成场景图: {scene_id}")
        
        img_path = self.gen.generate_image(
            prompt=prompt,
            model="nano-banana-fast",
            aspect_ratio="16:9",
            image_size="2K"
        )
        
        new_path = self._move_to_project(project_id, img_path, f"scenes/{scene_id}.png")
        
        return new_path
    
    def generate_storyboard(self, project_id, segment_id, edesc):
        """生成分镜图 (多图合成)"""
        print(f"\n🎬 生成分镜图: segment_{segment_id}")
        
        # TODO: 需要扩展image_generator支持多图输入
        # 暂时用纯提示词生成
        img_path = self.gen.generate_image(
            prompt=edesc,
            model="nano-banana-pro",
            aspect_ratio="16:9",
            image_size="2K"
        )
        
        new_path = self._move_to_project(project_id, img_path, f"storyboard/segment_{segment_id}.png")
        
        return new_path
    
    def _move_to_project(self, project_id, old_path, new_name):
        """移动图片到工程目录"""
        import shutil
        
        project_dir = Path("images") / project_id
        target_dir = project_dir / Path(new_name).parent
        target_dir.mkdir(parents=True, exist_ok=True)
        
        new_path = project_dir / new_name
        shutil.move(old_path, new_path)
        
        return str(new_path)