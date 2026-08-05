import json
import re
from typing import Any

from app.core.config import settings


class AiEvaluator:
    """Call an OpenAI-compatible chat endpoint without exposing credentials to the browser."""

    def evaluate(self, packet: dict[str, Any]) -> dict[str, Any]:
        if not settings.ai_api_key or not settings.ai_model:
            return {
                "status": "not_configured",
                "summary": "AI 评估暂不可用，请联系管理员。",
                "model": None,
            }

        prompt = {
            "asset": packet["asset"],
            "period": packet["period"],
            "factors": packet["factors"],
            "market_sentiment": packet["market_sentiment"],
            "asset_news": packet["asset_news"],
        }
        system_prompt = (
            "你是量化研究助手。只根据输入数据做谨慎、可审计的评估，不要编造缺失数据。"
            "请为每个量化、财务、宏观、资金流、财报因子独立返回 score，并为市场情绪、资产相关新闻和 overall 各返回一个 score。"
            "因子、市场情绪、资产相关新闻这三类单项 score 必须返回 -10 到 +10 之间的整数：-10 表示强利空，-5 表示中等利空，0 表示真正中性，+5 表示中等利多，+10 表示强利多。"
            "overall 必须单独返回 -1 到 +1 之间的小数，并保留两位小数。"
            "请根据数据的方向、幅度、同比/环比、预测差异、收益、波动、回撤、资金流和新闻倾向判断，不要因为谨慎就把所有单项打成 0 或 5。"
            "只有证据确实中性时才使用 0；某一项没有足够证据时返回 null 并在 summary 说明，不要用 0 代替缺失数据。"
            "不同因子应体现实际信号强弱，单项评分要在 -10 到 +10 内充分区分，避免只使用 0、5、-5 等少数档位；不能为了制造分布而脱离数据。"
            "overall 应综合可用信号的方向和强弱，不要机械地全部取平均。"
            "必须只返回 JSON，不要 Markdown。示例中的数字仅用于说明格式，不要照抄："
            "{\"factor_scores\":{\"factor_key\":{\"score\":4,\"summary\":\"...\"}},"
            "\"market_sentiment\":{\"score\":-3,\"summary\":\"...\"},"
            "\"asset_news\":{\"score\":7,\"summary\":\"...\"},"
            "\"overall\":{\"score\":0.16,\"summary\":\"...\"}}。"
        )
        try:
            import httpx

            with httpx.Client(timeout=settings.ai_request_timeout) as client:
                response = client.post(
                    f"{settings.ai_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                    json={
                        "model": settings.ai_model,
                        "temperature": 0.2,
                        "thinking": {"type": "disabled"},
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, default=str)},
                        ],
                    },
                )
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                parsed = _parse_json(content)
                return {
                    "status": "ready",
                    "model": settings.ai_model,
                    **parsed,
                }
        except Exception as exc:
            return {
                "status": "error",
                "model": settings.ai_model,
                "summary": f"AI 评估请求失败（{_error_reason(exc)}），请联系管理员。",
            }


def _error_reason(error: Exception) -> str:
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code:
        return f"HTTP {status_code}"
    reason = str(error).strip().replace("\n", " ")
    return reason[:160] or error.__class__.__name__


def _parse_json(content: Any) -> dict[str, Any]:
    if isinstance(content, list):
        content = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content)
    text = str(content).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("AI response must be a JSON object")
    return parsed


def normalized_score(value: Any, *, scale: str = "overall") -> float | int | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if scale == "single":
        return int(max(-10, min(10, round(number))))
    return max(-1.0, min(1.0, round(number, 2)))


def evaluation_score(data: Any, fallback: dict[str, Any], *, scale: str = "overall") -> dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    score = normalized_score(data.get("score"), scale=scale)
    summary = str(data.get("summary") or fallback.get("summary") or "")
    fallback_status = fallback.get("status", "unavailable")
    status = "ready" if score is not None else (
        "not_configured" if fallback_status == "not_configured" else
        "error" if fallback_status == "error" else
        "unavailable"
    )
    return {
        "score": score,
        "status": status,
        "summary": summary,
        "model": fallback.get("model"),
    }
