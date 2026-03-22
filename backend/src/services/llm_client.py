"""
LLM Client per NVIDIA API - Llama 3.1
"""

import asyncio
import time
import json
import logging
import traceback
from typing import Optional, Dict, Any
from openai import AsyncOpenAI, RateLimitError, APIStatusError

from src.config import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "meta/llama-3.1-8b-instruct"


class LLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        self._last_call_time: float = 0.0
        self._lock = asyncio.Lock()
        logger.info(
            f"LLMClient init — key={settings.llm_api_key[:12]}... url={settings.llm_base_url}"
        )

    async def call(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.6,
    ) -> str:
        async with self._lock:
            elapsed = time.monotonic() - self._last_call_time
            if elapsed < settings.min_request_interval:
                await asyncio.sleep(settings.min_request_interval - elapsed)

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            logger.info(
                f">>> CALL model={DEFAULT_MODEL} max_tokens={max_tokens} msgs={len(messages)} prompt={repr(prompt[:100])}"
            )

            backoff = settings.backoff_base
            attempt = 0
            while True:
                attempt += 1
                try:
                    logger.info(f" attempt {attempt} — calling API...")
                    response = await self.client.chat.completions.create(
                        model=DEFAULT_MODEL,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stream=False,
                    )
                    self._last_call_time = time.monotonic()
                    content = response.choices[0].message.content or ""
                    logger.info(
                        f"<<< OK chars={len(content)} content={repr(content[:200])}"
                    )
                    return content

                except RateLimitError as e:
                    logger.warning(f" RateLimitError: {e} — backing off {backoff}s")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, settings.max_backoff)

                except APIStatusError as e:
                    logger.error(
                        f" APIStatusError status={e.status_code} body={e.body} message={e.message}"
                    )
                    if e.status_code in (500, 502, 503):
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, settings.max_backoff)
                    else:
                        raise

                except Exception as e:
                    logger.error(f" UNEXPECTED ERROR type={type(e).__name__} msg={e}")
                    logger.error(traceback.format_exc())
                    raise

    async def call_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.6,
    ) -> Dict[str, Any]:
        sys_msg = "Rispondi SOLO con JSON valido. Nessun testo extra. Nessun markdown."
        if system:
            sys_msg = system[:120].strip() + "\n" + sys_msg

        for attempt in range(3):
            try:
                raw = await self.call(
                    prompt=prompt,
                    system=sys_msg,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                if not raw or not raw.strip():
                    logger.warning(f"Risposta vuota tentativo {attempt + 1}")
                    await asyncio.sleep(1)
                    continue

                cleaned = raw.strip()
                if "```" in cleaned:
                    cleaned = "\n".join(
                        line
                        for line in cleaned.split("\n")
                        if not line.strip().startswith("```")
                    )

                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                if start >= 0 and end > start:
                    cleaned = cleaned[start:end]
                else:
                    logger.warning(f"Nessun JSON trovato in: {repr(cleaned[:300])}")
                    await asyncio.sleep(1)
                    continue

                return json.loads(cleaned)

            except json.JSONDecodeError as e:
                logger.warning(
                    f"JSON parse fallito tentativo {attempt + 1}: {e} | raw={repr(raw[:300])}"
                )
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(
                    f"call_json eccezione tentativo {attempt + 1}: {type(e).__name__}: {e}"
                )
                logger.error(traceback.format_exc())
                break

        logger.error("call_json fallito dopo 3 tentativi — ritorno {}")
        return {}


llm_client = LLMClient()
