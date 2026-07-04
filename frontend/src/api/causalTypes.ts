// backend/app/causal/effect_estimation.py の CausalEffectResult に対応するTS型定義

export interface CausalEffectResult {
  treatment_node_id: string;
  outcome_node_id: string;
  method_name: string;
  backdoor_variables: string[];
  estimated_effect: number;
}
