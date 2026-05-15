from __future__ import annotations

from collections import defaultdict

from ashare_alpha.data import StockMaster
from ashare_alpha.factors import FactorDailyRecord
from ashare_alpha.scoring.models import ComponentScore


def compute_industry_strength_scores(
    stock_master: list[StockMaster],
    factor_records: list[FactorDailyRecord],
    min_industry_count: int = 2,
) -> dict[str, ComponentScore]:
    stock_by_code = {stock.ts_code: stock for stock in stock_master}
    factors_by_code = {record.ts_code: record for record in factor_records}
    momentum_by_industry: dict[str, list[float]] = defaultdict(list)

    for code, factor in factors_by_code.items():
        stock = stock_by_code.get(code)
        if stock is None or not stock.industry or not factor.is_computable or factor.momentum_20d is None:
            continue
        momentum_by_industry[stock.industry].append(factor.momentum_20d)

    eligible_avgs = {
        industry: sum(values) / len(values)
        for industry, values in momentum_by_industry.items()
        if len(values) >= min_industry_count
    }
    ranked_industries = sorted(eligible_avgs, key=lambda industry: eligible_avgs[industry])
    scores_by_industry = {
        industry: _percentile_score(index, len(ranked_industries))
        for index, industry in enumerate(ranked_industries)
    }

    results: dict[str, ComponentScore] = {}
    for stock in stock_master:
        if not stock.industry:
            results[stock.ts_code] = ComponentScore(score=50.0, reasons=["行业缺失，行业强度使用中性分"])
            continue
        if stock.industry not in scores_by_industry:
            results[stock.ts_code] = ComponentScore(score=50.0, reasons=["行业可计算样本不足，行业强度使用中性分"])
            continue
        score = scores_by_industry[stock.industry]
        avg_momentum = eligible_avgs[stock.industry]
        results[stock.ts_code] = ComponentScore(
            score=score,
            reasons=[f"所属行业20日平均动量 {avg_momentum:.2%}，行业强度分 {score:.1f}"],
            risk_reasons=[] if score >= 50 else ["所属行业横截面动量偏弱"],
        )
    return results


def _percentile_score(index: int, total: int) -> float:
    if total <= 1:
        return 50.0
    return 100 * index / (total - 1)
