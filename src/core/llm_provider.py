from abc import ABC, abstractmethod
import os
import requests
import json

class ILLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str) -> str:
        """
        프롬프트와 시스템 프롬프트를 받아 LLM의 응답(주로 JSON 문자열)을 반환합니다.
        """
        pass

class MockLLMProvider(ILLMProvider):
    def __init__(self, predefined_responses: list):
        self.responses = predefined_responses
        
    def generate(self, prompt: str, system_prompt: str) -> str:
        if not self.responses:
            # 기본 동작: 빈 응답 리스트일 경우 예외 대신 더미 JSON 반환 (UI 데모용)
            return '{"type": "WAIT", "duration_sec": 1.0}'
        return self.responses.pop(0)

class LocalCPUProvider(ILLMProvider):
    def __init__(self, endpoint: str, model_name: str, timeout_sec: int = 120):
        self.endpoint = endpoint
        self.model_name = model_name
        self.timeout_sec = int(timeout_sec)
        
    def generate(self, prompt: str, system_prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "prompt": f"{system_prompt}\n\n{prompt}",
            "stream": False,
            "format": "json" # Ollama JSON 모드 강제
        }
        try:
            response = requests.post(self.endpoint, json=payload, timeout=self.timeout_sec)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except Exception as e:
            raise RuntimeError(f"Local LLM Request Failed: {str(e)}")

class OpenAIProvider(ILLMProvider):
    def __init__(self, api_key: str, model_name: str, temperature: float = 0.1):
        import openai
        if not api_key or api_key == "${OPENAI_API_KEY}":
             api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
             raise ValueError("OPENAI_API_KEY is missing.")
             
        self.client = openai.OpenAI(api_key=api_key)
        self.model_name = model_name
        self.temperature = float(temperature)
        
    def generate(self, prompt: str, system_prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={ "type": "json_object" } # JSON 강제
            )
            return response.choices[0].message.content
        except Exception as e:
             raise RuntimeError(f"OpenAI Request Failed: {str(e)}")

    def __init__(self, api_key: str, model_name: str, temperature: float = 0.1):
        import google.generativeai as genai
        self.genai = genai
        if not api_key or api_key == "${GEMINI_API_KEY}":
             api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
             raise ValueError("GEMINI_API_KEY is missing.")
             
        self.genai.configure(api_key=api_key)
        self.model = self.genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.genai.GenerationConfig(
                temperature=temperature,
                # Fixed: Use proper configuration for JSON mode if supported by the library version
                response_mime_type="application/json"
            )
        )
        
    def generate(self, prompt: str, system_prompt: str) -> str:
        try:
            full_prompt = f"System Instruction: {system_prompt}\n\nUser Output Goal:\n{prompt}"
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
             raise RuntimeError(f"Gemini Request Failed: {str(e)}")

class LLMFactory:
    @staticmethod
    def create_provider(config: dict) -> ILLMProvider:
        llm_type = config.get("type", "local").lower()
        
        if llm_type == "mock":
            # 테스트용. 실제 환경에선 주입 방식을 더 권장합니다.
            return MockLLMProvider([])
            
        elif llm_type == "local":
            c = config.get("local", {})
            return LocalCPUProvider(
                endpoint=c.get("endpoint", "http://localhost:11434/api/generate"),
                model_name=c.get("model_name", "llama3"),
                timeout_sec=c.get("timeout_sec", 120)
            )
            
        elif llm_type == "openai":
            c = config.get("openai", {})
            return OpenAIProvider(
                api_key=c.get("api_key", ""),
                model_name=c.get("model_name", "gpt-4o"),
                temperature=c.get("temperature", 0.1)
            )
            
        elif llm_type == "gemini":
            c = config.get("gemini", {})
            return GeminiProvider(
                api_key=c.get("api_key", ""),
                model_name=c.get("model_name", "gemini-1.5-pro"),
                temperature=c.get("temperature", 0.1)
            )
            
        else:
            raise ValueError(f"Unknown LLM Provider type: {llm_type}")
