import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config):
        self.config = config
        self._provider = config.LLM_PROVIDER

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
        if self._provider == "openai":
            return self._generate_openai(prompt, system_prompt, temperature)
        elif self._provider == "gigachat":
            return self._generate_gigachat(prompt, system_prompt, temperature)
        elif self._provider == "yandex":
            return self._generate_yandex(prompt, system_prompt, temperature)
        elif self._provider == "ollama":
            return self._generate_ollama(prompt, system_prompt, temperature)
        else:
            raise ValueError(f"Unknown LLM provider: {self._provider}")

    def _generate_openai(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=self.config.OPENAI_API_KEY)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    def _generate_gigachat(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        import uuid
        auth_token = self._get_gigachat_token()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        resp = httpx.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
                "X-Request-ID": str(uuid.uuid4()),
            },
            json={
                "model": "GigaChat",
                "messages": messages,
                "temperature": temperature,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _get_gigachat_token(self) -> str:
        import uuid
        resp = httpx.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={
                "Authorization": f"Basic {self.config.GIGACHAT_CREDENTIALS}",
                "Content-Type": "application/x-www-form-urlencoded",
                "RqUID": str(uuid.uuid4()),
                "Accept": "application/json",
            },
            data={"scope": self.config.GIGACHAT_SCOPE},
            timeout=30,
            verify=False,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _generate_yandex(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "text": system_prompt})
        messages.append({"role": "user", "text": prompt})
        resp = httpx.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers={
                "Authorization": f"Api-Key {self.config.YANDEX_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "modelUri": f"gpt://{self.config.YANDEX_FOLDER_ID}/yandexgpt/latest",
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature,
                },
                "messages": messages,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["result"]["alternatives"][0]["message"]["text"]

    def _generate_ollama(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        payload = {
            "model": self.config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["system"] = system_prompt
        resp = httpx.post(
            f"{self.config.OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")
