# Unit tests for data_quality_checks module
# Co-authored with CoCo
import pandas as pd
import pytest
from data_quality_checks import check_empty, check_stale, check_range, run_all_checks, log_warnings


class TestCheckEmpty:
    def test_empty_df_returns_warning(self):
        df = pd.DataFrame()
        result = check_empty(df, "GDP")
        assert result is not None
        assert result["check"] == "empty_data"
        assert result["indicator"] == "GDP"

    def test_none_df_returns_warning(self):
        result = check_empty(None, "CPI")
        assert result is not None
        assert result["indicator"] == "CPI"

    def test_populated_df_returns_none(self):
        df = pd.DataFrame({"DATE": ["2024-01-01"], "VALUE": [1.5]})
        result = check_empty(df, "GDP")
        assert result is None


class TestCheckStale:
    def test_stale_data_returns_warning(self):
        old_date = pd.Timestamp.now() - pd.Timedelta(days=200)
        df = pd.DataFrame({"DATE": [old_date]})
        result = check_stale(df, "DATE", "GDP", max_age_days=120)
        assert result is not None
        assert result["check"] == "stale_data"

    def test_fresh_data_returns_none(self):
        recent_date = pd.Timestamp.now() - pd.Timedelta(days=30)
        df = pd.DataFrame({"DATE": [recent_date]})
        result = check_stale(df, "DATE", "GDP", max_age_days=120)
        assert result is None

    def test_empty_df_returns_none(self):
        result = check_stale(pd.DataFrame(), "DATE", "GDP")
        assert result is None

    def test_none_df_returns_none(self):
        result = check_stale(None, "DATE", "GDP")
        assert result is None

    def test_custom_threshold(self):
        old_date = pd.Timestamp.now() - pd.Timedelta(days=10)
        df = pd.DataFrame({"DATE": [old_date]})
        result = check_stale(df, "DATE", "GDP", max_age_days=5)
        assert result is not None

    def test_boundary_exactly_at_threshold(self):
        boundary_date = pd.Timestamp.now() - pd.Timedelta(days=120)
        df = pd.DataFrame({"DATE": [boundary_date]})
        # At exactly the threshold, should be flagged (< not <=)
        result = check_stale(df, "DATE", "GDP", max_age_days=120)
        assert result is not None


class TestCheckRange:
    def test_value_above_max_returns_warning(self):
        df = pd.DataFrame({"RATE": [5.0, 35.0]})
        result = check_range(df, "RATE", "Unemployment", 0, 30)
        assert result is not None
        assert result["check"] == "anomalous_value"

    def test_value_below_min_returns_warning(self):
        df = pd.DataFrame({"RATE": [-1.0, 5.0]})
        result = check_range(df, "RATE", "Unemployment", 0, 30)
        assert result is not None

    def test_values_in_range_returns_none(self):
        df = pd.DataFrame({"RATE": [3.5, 4.2, 5.1]})
        result = check_range(df, "RATE", "Unemployment", 0, 30)
        assert result is None

    def test_empty_df_returns_none(self):
        result = check_range(pd.DataFrame(), "RATE", "Test", 0, 100)
        assert result is None

    def test_none_df_returns_none(self):
        result = check_range(None, "RATE", "Test", 0, 100)
        assert result is None

    def test_boundary_at_max_returns_none(self):
        df = pd.DataFrame({"RATE": [30.0]})
        result = check_range(df, "RATE", "Unemployment", 0, 30)
        assert result is None

    def test_boundary_at_min_returns_none(self):
        df = pd.DataFrame({"RATE": [0.0]})
        result = check_range(df, "RATE", "Unemployment", 0, 30)
        assert result is None


class TestRunAllChecks:
    def _make_valid_dfs(self):
        recent = pd.Timestamp.now() - pd.Timedelta(days=30)
        gdp = pd.DataFrame({"DATE": [recent], "GDP_PCT_CHANGE": [2.1]})
        unemp = pd.DataFrame({"DATE": [recent], "UNEMPLOYMENT_RATE": [4.2]})
        fed = pd.DataFrame({"DATE": [recent], "FED_FUNDS_RATE": [5.25]})
        cpi = pd.DataFrame({"DATE": [recent], "CPI_INDEX": [320.0], "CPI_YOY": [3.1]})
        return gdp, unemp, fed, cpi

    def test_all_valid_returns_empty(self):
        gdp, unemp, fed, cpi = self._make_valid_dfs()
        warnings = run_all_checks(gdp, unemp, fed, cpi)
        assert warnings == []

    def test_empty_gdp_flagged(self):
        _, unemp, fed, cpi = self._make_valid_dfs()
        warnings = run_all_checks(pd.DataFrame(), unemp, fed, cpi)
        assert any(w["indicator"] == "GDP" and w["check"] == "empty_data" for w in warnings)

    def test_stale_unemployment_flagged(self):
        gdp, unemp, fed, cpi = self._make_valid_dfs()
        old_date = pd.Timestamp.now() - pd.Timedelta(days=200)
        unemp["DATE"] = [old_date]
        warnings = run_all_checks(gdp, unemp, fed, cpi)
        assert any(w["indicator"] == "Unemployment" and w["check"] == "stale_data" for w in warnings)

    def test_anomalous_fed_rate_flagged(self):
        gdp, unemp, fed, cpi = self._make_valid_dfs()
        fed["FED_FUNDS_RATE"] = [30.0]
        warnings = run_all_checks(gdp, unemp, fed, cpi)
        assert any(w["indicator"] == "Fed Funds" and w["check"] == "anomalous_value" for w in warnings)

    def test_cpi_over_20_flagged(self):
        gdp, unemp, fed, cpi = self._make_valid_dfs()
        cpi["CPI_YOY"] = [25.0]
        warnings = run_all_checks(gdp, unemp, fed, cpi)
        assert any(w["indicator"] == "CPI" and w["check"] == "anomalous_value" for w in warnings)


class TestLogWarnings:
    def test_warnings_appended_to_log(self):
        warnings = [{"check": "stale_data", "indicator": "GDP", "message": "Stale"}]
        log = []
        result = log_warnings(warnings, log)
        assert len(result) == 1
        assert result[0]["check"] == "stale_data"
        assert "timestamp" in result[0]

    def test_clean_run_logged(self):
        log = []
        result = log_warnings([], log)
        assert len(result) == 1
        assert result[0]["check"] == "all_passed"

    def test_multiple_warnings_all_logged(self):
        warnings = [
            {"check": "empty_data", "indicator": "GDP", "message": "Empty"},
            {"check": "stale_data", "indicator": "CPI", "message": "Stale"},
        ]
        log = []
        result = log_warnings(warnings, log)
        assert len(result) == 2

    def test_existing_log_preserved(self):
        existing = [{"timestamp": "2024-01-01", "check": "all_passed", "indicator": "—", "message": "OK"}]
        result = log_warnings([], existing)
        assert len(result) == 2
        assert result[0]["timestamp"] == "2024-01-01"
