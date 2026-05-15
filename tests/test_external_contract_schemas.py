from __future__ import annotations

from ashare_alpha.data.contracts.schemas import get_external_contracts


def test_tushare_like_contract_contains_four_datasets() -> None:
    contracts = get_external_contracts("tushare_like")

    assert {contract.dataset_name for contract in contracts} == {
        "stock_basic",
        "daily",
        "fina_indicator",
        "announcements",
    }


def test_akshare_like_contract_contains_four_datasets() -> None:
    contracts = get_external_contracts("akshare_like")

    assert {contract.dataset_name for contract in contracts} == {
        "stock_info",
        "stock_zh_a_hist",
        "financial_abstract",
        "stock_notice",
    }


def test_each_contract_has_target_dataset_name() -> None:
    for source_name in ("tushare_like", "akshare_like"):
        assert all(contract.target_dataset_name for contract in get_external_contracts(source_name))
