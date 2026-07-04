"""dowhy==0.8とpandas 2.0以降の非互換を吸収する最小限のモンキーパッチ。

dowhyのRegressionEstimator._estimate_effectは `self.model.params[0]` のように
Seriesへ整数インデックスでアクセスしており、pandasが2.0で廃止した
「ラベルがinteger型でない場合の位置指定フォールバック」に依存している。
ライブラリ本体は書き換えず、該当メソッドのみ`.iloc`を使う版に差し替える。
"""

from __future__ import annotations

from dowhy.causal_estimator import CausalEstimate
from dowhy.causal_estimators.regression_estimator import RegressionEstimator

_PATCHED = False


def _patched_estimate_effect(self, data_df=None, need_conditional_estimates=None):
    if data_df is None:
        data_df = self._data
    if need_conditional_estimates is None:
        need_conditional_estimates = self.need_conditional_estimates
    if not self.model:
        _, self.model = self._build_model()

    effect_estimate = self._do(self._treatment_value, data_df) - self._do(self._control_value, data_df)
    conditional_effect_estimates = None
    if need_conditional_estimates:
        conditional_effect_estimates = self._estimate_conditional_effects(
            self._estimate_effect_fn, effect_modifier_names=self._effect_modifier_names
        )
    intercept_parameter = self.model.params.iloc[0]
    return CausalEstimate(
        estimate=effect_estimate,
        control_value=self._control_value,
        treatment_value=self._treatment_value,
        conditional_estimates=conditional_effect_estimates,
        target_estimand=self._target_estimand,
        realized_estimand_expr=self.symbolic_estimator,
        intercept=intercept_parameter,
    )


def apply_dowhy_pandas_compat_patch() -> None:
    global _PATCHED
    if _PATCHED:
        return
    RegressionEstimator._estimate_effect = _patched_estimate_effect
    _PATCHED = True
