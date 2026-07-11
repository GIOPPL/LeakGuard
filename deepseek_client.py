import requests
import json
import re

SYSTEM_PROMPT = """你是一位密码安全专家。用户的请求是想要一个基于特定风格/记忆点的强密码。
请分析用户输入的风格特征，生成10个既安全又好记的密码变体。

规则：
1. 每个密码长度必须在12-20位之间
2. 必须包含大小写字母、数字、特殊符号中的至少3种
3. 不能是常见字典单词的直接变体
4. 要保留用户的记忆点，但通过安全手段增强（如leet speak、插入符号、大小写混淆）
5. 返回严格JSON格式，不要其他解释

输出格式：
{
  "passwords": [
    {"value": "示例密码1", "strength": "强", "reason": "推荐理由1"},
    {"value": "示例密码2", "strength": "强", "reason": "推荐理由2"}
  ],
  "suggestion": "总体建议"
}"""


class DeepSeekClient:
    def __init__(self, api_key, base_url="https://api.deepseek.com", model="deepseek-chat", temperature=0.8):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature

    def optimize_password(self, user_input):
        """根据用户输入的密码风格，AI生成10组建议密码"""
        if not self.api_key:
            raise ValueError("API Key 未配置")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            "temperature": self.temperature,
            "max_tokens": 1500
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return self._parse_response(content)
        except requests.exceptions.Timeout:
            raise RuntimeError("请求超时，请检查网络或代理设置")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise RuntimeError("API Key 无效或已过期")
            elif response.status_code == 429:
                raise RuntimeError("请求过于频繁，请稍后再试")
            else:
                raise RuntimeError(f"API 请求失败: {response.status_code}")
        except Exception as e:
            raise RuntimeError(f"调用失败: {str(e)}")

    def _parse_response(self, content):
        """解析 AI 返回的内容，提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试从代码块中提取
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试从花括号中提取
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise RuntimeError("AI 返回格式异常，无法解析")
