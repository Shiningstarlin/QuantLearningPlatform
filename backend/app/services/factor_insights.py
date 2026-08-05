import logging
import math
import re
from datetime import date, datetime, timedelta, timezone
from statistics import mean, stdev
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.insights import FactorInsightsRead
from app.services.ai_evaluator import AiEvaluator, evaluation_score
from app.services.market_board import MarketBoardService

logger = logging.getLogger(__name__)


class FactorInsightsService:
    """Build a time-bounded research packet from Futu and optionally score it with AI."""

    def __init__(self, db: Session):
        self.db = db

    def get_insights(self, asset_id: int, start_date: date, end_date: date) -> FactorInsightsRead:
        today = datetime.now(timezone.utc).date()
        if end_date < start_date:
            raise HTTPException(status_code=400, detail="end_date must be on or after start_date")
        if end_date > today:
            raise HTTPException(status_code=400, detail="The insight period cannot end in the future")
        if (end_date - start_date).days > 365:
            raise HTTPException(status_code=400, detail="The insight period cannot exceed 365 days")

        asset = MarketBoardService(self.db).get_asset(asset_id)
        result: dict[str, Any] = {
            "asset": asset,
            "start_date": start_date,
            "end_date": end_date,
            "generated_at": datetime.now(timezone.utc),
            "factors": [],
            "market_sentiment": {
                "title": "市场情绪（热度代理）",
                "source": "Futu get_hot_list + price/flow signals",
                "available": False,
                "indicators": [],
            },
            "asset_news": {
                "title": "资产相关新闻",
                "source": "Futu get_search_news",
                "available": False,
                "items": [],
            },
            "warnings": [],
        }

        packet = {
            "asset": {"symbol": asset.symbol, "name": asset.name, "exchange": asset.exchange},
            "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "factors": [],
            "market_sentiment": [],
            "asset_news": [],
        }

        try:
            self._collect_futu_data(result, packet, asset.symbol, asset.exchange, start_date, end_date)
        except Exception as exc:
            logger.warning("Factor insight collection failed for %s: %s", asset.symbol, _safe_error(exc))
            result["warnings"].append(f"Futu 数据读取失败：{_safe_error(exc)}")

        if not result["factors"]:
            self._collect_local_quote_fallback(result, asset_id, start_date, end_date)

        packet["factors"] = [_factor_for_ai(factor) for factor in result["factors"]]
        packet["market_sentiment"] = [_factor_for_ai(factor) for factor in result["market_sentiment"]["indicators"]]
        packet["asset_news"] = result["asset_news"]["items"]

        ai_result = AiEvaluator().evaluate(packet)
        ai_fallback = {
            "score": None,
            "status": ai_result.get("status", "unavailable"),
            "summary": ai_result.get("summary", ""),
            "model": ai_result.get("model"),
        }
        factor_scores = ai_result.get("factor_scores", {}) if isinstance(ai_result, dict) else {}
        for factor in result["factors"]:
            factor["ai"] = evaluation_score(
                factor_scores.get(factor["key"]) if isinstance(factor_scores, dict) else None,
                {**ai_fallback, "summary": "AI 未返回该因子的评估值。" if ai_fallback["status"] == "ready" else ai_fallback["summary"]},
                scale="single",
            )

        result["market_sentiment"]["ai"] = evaluation_score(
            ai_result.get("market_sentiment") if isinstance(ai_result, dict) else None,
            ai_fallback,
            scale="single",
        )
        result["asset_news"]["ai"] = evaluation_score(
            ai_result.get("asset_news") if isinstance(ai_result, dict) else None,
            ai_fallback,
            scale="single",
        )
        result["overall"] = evaluation_score(
            ai_result.get("overall") if isinstance(ai_result, dict) else None,
            ai_fallback,
        )
        result["ai_configured"] = bool(settings.ai_api_key and settings.ai_model)

        if not result["ai_configured"]:
            result["warnings"].append("AI 评估暂时不可用，请联系管理员。")
        return FactorInsightsRead.model_validate(result)

    def _collect_futu_data(
        self,
        result: dict[str, Any],
        packet: dict[str, Any],
        symbol: str,
        exchange: str,
        start_date: date,
        end_date: date,
    ) -> None:
        try:
            from futu import AuType, KLType, MacroRegion, Market, OpenQuoteContext, PeriodType, RET_OK
        except ImportError as exc:
            raise RuntimeError("后端未安装 futu-api，请先安装依赖。") from exc

        context = None
        try:
            context = OpenQuoteContext(host=settings.futu_host, port=settings.futu_port)
            all_bars = self._history_bars(context, symbol, start_date, end_date, KLType, AuType, RET_OK)
            period_bars = [bar for bar in all_bars if start_date <= _to_date(bar.get("time_key")) <= end_date]
            if period_bars:
                self._add_quant_factors(result, period_bars, all_bars, start_date, end_date)
                packet["factors"].extend(_factor_for_ai(factor) for factor in result["factors"])
            else:
                result["warnings"].append("Futu 未返回查询区间内的日 K 线数据。")

            self._collect_capital_flow(result, context, symbol, start_date, end_date, PeriodType, RET_OK)
            self._collect_financials(result, context, symbol, RET_OK)
            self._collect_earnings(result, context, symbol, exchange, start_date, end_date, Market, RET_OK)
            self._collect_macro(result, context, exchange, start_date, end_date, MacroRegion, RET_OK)
            self._collect_sentiment(result, context, symbol, exchange, Market, RET_OK)
            asset_name = getattr(result.get("asset"), "name", "")
            self._collect_news(result, context, symbol, asset_name, start_date, end_date, RET_OK)
        finally:
            if context is not None:
                context.close()

    @staticmethod
    def _history_bars(context, symbol, start_date, end_date, kl_type, au_type, ret_ok):
        warmup_start = start_date - timedelta(days=60)
        ret, frame, page_key = context.request_history_kline(
            symbol,
            start=warmup_start.isoformat(),
            end=end_date.isoformat(),
            ktype=kl_type.K_DAY,
            autype=au_type.QFQ,
            max_count=1000,
        )
        if ret != ret_ok:
            raise RuntimeError(str(frame))
        records = _frame_records(frame)
        while page_key is not None:
            ret, frame, page_key = context.request_history_kline(
                symbol,
                start=warmup_start.isoformat(),
                end=end_date.isoformat(),
                ktype=kl_type.K_DAY,
                autype=au_type.QFQ,
                max_count=1000,
                page_req_key=page_key,
            )
            if ret != ret_ok:
                raise RuntimeError(str(frame))
            records.extend(_frame_records(frame))
        return sorted(records, key=lambda row: str(row.get("time_key", "")))

    @staticmethod
    def _add_quant_factors(result, period_bars, all_bars, start_date, end_date):
        closes = [_number(row.get("close")) for row in all_bars]
        closes = [value for value in closes if value is not None and value > 0]
        period_closes = [_number(row.get("close")) for row in period_bars]
        period_closes = [value for value in period_closes if value is not None and value > 0]
        volumes = [_number(row.get("volume")) for row in all_bars]
        volumes = [value for value in volumes if value is not None and value >= 0]
        period_volumes = [_number(row.get("volume")) for row in period_bars]
        period_volumes = [value for value in period_volumes if value is not None and value >= 0]
        if len(period_closes) >= 2:
            period_return = period_closes[-1] / period_closes[0] - 1
            result["factors"].append(_factor("period_return", "区间收益", "quant", period_return * 100, "%", end_date.isoformat(), f"{start_date} 至 {end_date}"))
            drawdown = _max_drawdown(period_closes)
            result["factors"].append(_factor("period_max_drawdown", "区间最大回撤", "quant", drawdown * 100, "%", end_date.isoformat(), f"{start_date} 至 {end_date}"))
        returns = [closes[index] / closes[index - 1] - 1 for index in range(1, len(closes)) if closes[index - 1] > 0]
        if len(returns) >= 2:
            volatility = stdev(returns) * math.sqrt(252) * 100
            result["factors"].append(_factor("annualized_volatility", "年化波动率", "quant", volatility, "%", end_date.isoformat(), "基于日收益率"))
        if len(closes) >= 15:
            gains = [max(value, 0) for value in [closes[index] - closes[index - 1] for index in range(len(closes) - 14, len(closes))]]
            losses = [max(-value, 0) for value in [closes[index] - closes[index - 1] for index in range(len(closes) - 14, len(closes))]]
            rsi = 100 if not sum(losses) else 100 - 100 / (1 + sum(gains) / sum(losses))
            result["factors"].append(_factor("rsi_14", "RSI(14)", "quant", rsi, "", end_date.isoformat(), "越接近 70/30 越值得关注"))
        if len(period_volumes) >= 1 and len(volumes) > len(period_volumes):
            baseline = volumes[: -len(period_volumes)]
            baseline_mean = mean(baseline[-20:]) if baseline else 0
            current_mean = mean(period_volumes)
            if baseline_mean > 0:
                result["factors"].append(_factor("volume_change", "成交量相对变化", "quant", (current_mean / baseline_mean - 1) * 100, "%", end_date.isoformat(), "区间平均成交量相对前 20 个交易日"))

    @staticmethod
    def _collect_capital_flow(result, context, symbol, start_date, end_date, period_type, ret_ok):
        try:
            ret, frame = context.get_capital_flow(symbol, period_type=period_type.DAY, start=start_date.isoformat(), end=end_date.isoformat())
            if ret != ret_ok:
                raise RuntimeError(str(frame))
            records = _frame_records(frame)
            values = [_number(row.get("in_flow")) for row in records]
            values = [value for value in values if value is not None]
            if values:
                result["factors"].append(_factor("capital_flow", "区间净资金流", "flow", sum(values), "金额", end_date.isoformat(), "Futu 日周期资金流；正值代表净流入"))
        except Exception as exc:
            result["warnings"].append(f"资金流数据不可用：{_safe_error(exc)}")

    @staticmethod
    def _collect_financials(result, context, symbol, ret_ok):
        try:
            ret, data = context.get_financials_statements(symbol, num=4)
            if ret != ret_ok:
                raise RuntimeError(str(data))
            reports = data.get("report_list", []) if isinstance(data, dict) else []
            wanted = ("营业收入", "营业总收入", "净利润", "归母", "每股收益", "净资产收益率", "毛利率", "经营现金流")
            added = 0
            for report in reports[:2]:
                observed_at = str(report.get("date_time_str") or "")
                period = str(report.get("period_text") or "")
                for item in report.get("item_list", []):
                    label = str(item.get("display_name") or "")
                    if not label or not any(keyword in label for keyword in wanted):
                        continue
                    value = _number(item.get("data"))
                    if value is None:
                        continue
                    key = f"financial_{item.get('field_id', added)}_{observed_at or period}"
                    note_parts = []
                    if _number(item.get("yoy")) is not None:
                        note_parts.append(f"同比 {_number(item.get('yoy')):.2f}%")
                    if _number(item.get("qoq")) is not None:
                        note_parts.append(f"环比 {_number(item.get('qoq')):.2f}%")
                    result["factors"].append(_factor(key, label, "financial", value, "原始值", observed_at, period, "Futu get_financials_statements", "；".join(note_parts) or "最新可用财报期，可能早于查询区间"))
                    added += 1
                    if added >= 10:
                        return
        except Exception as exc:
            result["warnings"].append(f"财务报表不可用：{_safe_error(exc)}")

    @staticmethod
    def _collect_earnings(result, context, symbol, exchange, start_date, end_date, market, ret_ok):
        try:
            market_value = _market_value(exchange, market)
            rows = []
            window_start = start_date
            while window_start <= end_date:
                window_end = min(window_start + timedelta(days=6), end_date)
                ret, frame = context.get_earnings_calendar(
                    market=market_value,
                    begin_date=window_start.isoformat(),
                    end_date=window_end.isoformat(),
                )
                if ret != ret_ok:
                    raise RuntimeError(str(frame))
                rows.extend(
                    row for row in _frame_records(frame)
                    if str(row.get("security") or row.get("code") or "").upper() == symbol.upper()
                )
                window_start = window_end + timedelta(days=1)
            for row in rows:
                earnings_date = str(row.get("earnings_date") or "")
                for key, label, actual_name, predict_name in (
                    ("eps_surprise", "EPS 预期差", "eps_actual", "eps_predict"),
                    ("revenue_surprise", "营收预期差", "revenue_actual", "revenue_predict"),
                    ("ebit_surprise", "EBIT 预期差", "ebit_actual", "ebit_predict"),
                ):
                    actual = _number(row.get(actual_name))
                    predict = _number(row.get(predict_name))
                    if actual is None or predict in (None, 0):
                        continue
                    result["factors"].append(_factor(f"earnings_{key}", label, "earnings", (actual / abs(predict) - 1) * 100, "%", earnings_date, str(row.get("period_text") or ""), "Futu get_earnings_calendar", f"实际值 {actual:g}；预测值 {predict:g}"))
        except Exception as exc:
            result["warnings"].append(f"财报日历不可用：{_safe_error(exc)}")

    @staticmethod
    def _collect_macro(result, context, exchange, start_date, end_date, macro_region, ret_ok):
        try:
            region = macro_region_for_exchange(exchange, macro_region)
            ret, frame = context.get_macro_indicator_list(region=region)
            if ret != ret_ok:
                raise RuntimeError(str(frame))
            candidates = _frame_records(frame)
            keywords = ("CPI", "PPI", "GDP", "失业", "就业", "利率", "PMI", "零售", "工业", "非农", "通胀")
            candidates = [row for row in candidates if any(keyword.lower() in str(row.get("name") or "").lower() for keyword in keywords)][:8]
            for indicator in candidates:
                indicator_id = indicator.get("indicator_id")
                name = str(indicator.get("name") or indicator_id)
                if indicator_id is None:
                    continue
                history_ret, history = context.get_macro_indicator_history(indicator_id=indicator_id, time=end_date.isoformat(), max_count=4)
                if history_ret != ret_ok:
                    continue
                for row in _frame_records(history):
                    release_date = _to_date(row.get("release_time") or row.get("data_time"))
                    if release_date < start_date or release_date > end_date:
                        continue
                    value = _number(row.get("value"))
                    if value is None:
                        continue
                    note = f"预测 {row.get('predict_value')}；前值 {row.get('previous_value')}"
                    result["factors"].append(_factor(f"macro_{indicator_id}_{release_date}", name, "macro", value, str(row.get("unit_type") or ""), str(row.get("release_time") or release_date), "", "Futu get_macro_indicator_history", note))
        except Exception as exc:
            result["warnings"].append(f"宏观指标不可用：{_safe_error(exc)}")

    @staticmethod
    def _collect_sentiment(result, context, symbol, exchange, market, ret_ok):
        try:
            market_value = _market_value(exchange, market)
            ret, data = context.get_hot_list(market=market_value, count=200)
            if ret != ret_ok:
                raise RuntimeError(str(data))
            rows = _frame_records(data[1] if isinstance(data, tuple) and len(data) == 2 else data)
            row = next((candidate for candidate in rows if str(candidate.get("security") or candidate.get("code") or "").upper() == symbol.upper()), None)
            if row is None:
                result["warnings"].append("该资产当前不在 Futu 热议榜返回范围内，市场情绪代理暂无数据。")
                return
            labels = {
                "trade_heat": "交易热度",
                "trade_heat_change": "交易热度变化",
                "search_heat": "搜索热度",
                "search_heat_change": "搜索热度变化",
                "news_heat": "资讯热度",
                "news_heat_change": "资讯热度变化",
                "average_heat": "综合热度",
                "average_heat_change": "综合热度变化",
            }
            for key, label in labels.items():
                value = _number(row.get(key))
                if value is not None:
                    result["market_sentiment"]["indicators"].append(_factor(f"sentiment_{key}", label, "quant", value, "", None, "当前快照", "Futu get_hot_list", "热度不是方向性收益预测"))
            result["market_sentiment"]["available"] = bool(result["market_sentiment"]["indicators"])
        except Exception as exc:
            result["warnings"].append(f"市场情绪代理不可用：{_safe_error(exc)}")

    @staticmethod
    def _collect_news(result, context, symbol, name, start_date, end_date, ret_ok):
        try:
            ret, frame = context.get_search_news(symbol, max_count=30)
            if ret != ret_ok or not _frame_records(frame):
                if name:
                    ret, frame = context.get_search_news(name, max_count=30)
            if ret != ret_ok:
                raise RuntimeError(str(frame))
            records = _frame_records(frame)
            filtered = []
            for row in records:
                published = _try_date(row.get("publish_time"))
                if published is None or start_date <= published <= end_date:
                    filtered.append(row)
            for row in filtered[:20]:
                result["asset_news"]["items"].append({
                    "title": str(row.get("title") or ""),
                    "subtype": str(row.get("news_sub_type") or ""),
                    "source": str(row.get("source") or ""),
                    "publish_time": str(row.get("publish_time") or ""),
                    "url": str(row.get("url") or ""),
                    "related_securities": _list_strings(row.get("related_securities")),
                })
            result["asset_news"]["available"] = True
        except Exception as exc:
            result["warnings"].append(f"资产相关新闻不可用：{_safe_error(exc)}")

    def _collect_local_quote_fallback(self, result, asset_id, start_date, end_date):
        quotes = MarketBoardService(self.db).quote_history(asset_id, limit=400)
        period_quotes = [quote for quote in quotes if start_date <= quote.quote_time.date() <= end_date]
        if len(period_quotes) < 2:
            result["warnings"].append("本地行情缓存不足，无法计算完整量化因子。")
            return
        closes = [quote.price for quote in period_quotes]
        result["factors"].append(_factor("period_return", "区间收益（本地缓存）", "quant", (closes[-1] / closes[0] - 1) * 100, "%", end_date.isoformat(), "本地行情缓存"))
        result["factors"].append(_factor("period_max_drawdown", "区间最大回撤（本地缓存）", "quant", _max_drawdown(closes) * 100, "%", end_date.isoformat(), "本地行情缓存"))
        result["warnings"].append("Futu 历史 K 线不可用，以上量化因子使用行情看板本地缓存。")


def _factor(key, label, category, value, unit="", observed_at=None, period=None, source="Futu", note=""):
    return {
        "key": key,
        "label": label,
        "category": category,
        "value": round(value, 6) if isinstance(value, float) else value,
        "unit": unit,
        "observed_at": observed_at,
        "period": period,
        "source": source,
        "note": note,
    }


def _factor_for_ai(factor):
    return {key: factor.get(key) for key in ("key", "label", "category", "value", "unit", "observed_at", "period", "source", "note")}


def _frame_records(frame):
    if frame is None:
        return []
    if isinstance(frame, tuple):
        return _frame_records(frame[-1])
    if hasattr(frame, "to_dict"):
        return frame.to_dict(orient="records")
    if isinstance(frame, list):
        return [row if isinstance(row, dict) else {} for row in frame]
    return []


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _to_date(value):
    parsed = _try_date(value)
    return parsed or date.min


def _try_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.upper() in {"N/A", "NAN", "NONE"}:
        return None
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    match = re.search(r"(\d{1,2})/(\d{1,2})", text)
    if match:
        try:
            return date(datetime.now().year, int(match.group(1)), int(match.group(2)))
        except ValueError:
            return None
    return None


def _max_drawdown(values):
    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = min(max_drawdown, value / peak - 1)
    return max_drawdown


def _market_value(exchange, market):
    exchange = (exchange or "").upper()
    if exchange.startswith("HK"):
        return market.HK
    if exchange.startswith("US"):
        return market.US
    if exchange.startswith("SH"):
        return market.SH
    if exchange.startswith("SZ"):
        return market.SZ
    return market.US


def macro_region_for_exchange(exchange, macro_region):
    exchange = (exchange or "").upper()
    mapping = {"HK": "HK", "US": "US", "SH": "CN", "SZ": "CN", "CN": "CN"}
    region_name = mapping.get(exchange.split(".", 1)[0], "US")
    return getattr(macro_region, region_name, macro_region.US)


def _list_strings(value):
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return []


def _safe_error(exc):
    message = str(exc).strip().replace("\n", " ")
    return message[:180] or exc.__class__.__name__
