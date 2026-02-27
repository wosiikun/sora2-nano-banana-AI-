"""
Agent处理逻辑模块
"""
import json
from api_client import DeepSeekClient
from prompts import PromptTemplates

class StoryAgent:
    def __init__(self):
        self.client = DeepSeekClient()
        self.prompts = PromptTemplates()
    
    def step1_generate_script_prompt(self, theme):
        """Step1: 生成文案生成提示词"""
        prompt = self.prompts.step1_template().format(theme=theme)
        return self.client.call(prompt)
    
    def step2_generate_script(self, script_prompt):
        """Step2: 生成文案"""
        return self.client.call(script_prompt)
    
    def step3_generate_base_storyboard(self, script, theme):
        """Step3: 生成基础分镜JSON"""
        prompt = self.prompts.step3_template(script, theme)
        result = self.client.call(prompt)
        
        # 尝试解析JSON
        try:
            # 清理可能的markdown标记
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            
            json_data = json.loads(cleaned)
            return json.dumps(json_data, ensure_ascii=False, indent=2)
        except:
            return result
    
    def step4_extract_characters_scenes(self, base_json):
        """Step4: 提取人物场景提示词"""
        prompt = self.prompts.step4_template(base_json)
        return self.client.call(prompt)
    
    def step5_generate_final_storyboard(self, base_json, character_scene):
        """Step5: 生成完整分镜JSON"""
        prompt = self.prompts.step5_template(base_json, character_scene)
        result = self.client.call(prompt)
        
        # 尝试解析JSON
        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            
            json_data = json.loads(cleaned)
            return json_data
        except:
            return result