"""
API客户端模块
"""
from openai import OpenAI

class DeepSeekClient:
    def __init__(self):
        self.client = OpenAI(
            api_key='sk-a2e28559994a4129bf6b2282ba034e6e',
            base_url="https://api.deepseek.com"
        )
    
    def call(self, prompt, system_msg="你是一个专业的AI助手"):
        """调用API"""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"API调用错误: {str(e)}"