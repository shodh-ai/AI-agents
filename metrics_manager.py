import json
import os
import random
from typing import Dict, Any, Optional, Tuple

class MetricsManager:
    def __init__(self, metrics_file: str = "metrics_data.json"):
        self.metrics_file = metrics_file
        self.metrics_data = self._load_metrics_data()
        
    def _load_metrics_data(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading metrics data: {str(e)}")
            return {}
            
    def _save_metrics_data(self) -> None:
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics_data, f, indent=4)
        except Exception as e:
            print(f"Error saving metrics data: {str(e)}")
            
    def get_metric_constraints(self, metric_type: str, department: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        if metric_type == "core":
            return self.metrics_data.get("metrics_definitions", {}).get("core", {})
        elif department:
            return self.metrics_data.get("metrics_definitions", {}).get("department", {}).get(department.upper(), {})
        return {}
        
    def get_week_metrics(self, week: int) -> Dict[str, Any]:
        return self.metrics_data.get("weekly_metrics", {}).get(f"week{week}", {})
        
    def apply_uncertainty(self, change: float, uncertainty: float) -> Tuple[float, float]:
        actual_change = random.uniform(change - uncertainty, change + uncertainty)
        return actual_change, uncertainty
        
    def update_week_metrics(self, week: int, department: str, changes: Dict[str, float]) -> Dict[str, Dict[str, Tuple[float, float]]]:
        week_key = f"week{week}"
        actual_changes = {"core": {}, "department": {}}
        
        if week_key not in self.metrics_data.get("weekly_metrics", {}):
            prev_week = self.get_week_metrics(week - 1) if week > 1 else {}
            self.metrics_data.setdefault("weekly_metrics", {})[week_key] = {
                "core": prev_week.get("core", {}),
                "department": {
                    department: prev_week.get("department", {}).get(department, {})
                },
                "changes": {}
            }
            
        week_data = self.metrics_data["weekly_metrics"][week_key]
        for metric, change in changes.items():
            category, metric_name = metric.split('.')
            constraints = self.get_metric_constraints(category, department if category == "department" else None)
            uncertainty = constraints[metric_name].get("uncertainty_range", 0)
            
            actual_change, uncertainty_used = self.apply_uncertainty(change, uncertainty)
            
            if category == "core":
                current = week_data["core"].get(metric_name, 0)
                week_data["core"][metric_name] = current * (1 + actual_change/100)
                actual_changes["core"][metric_name] = (actual_change, uncertainty_used)
            elif category == "department":
                if department not in week_data["department"]:
                    week_data["department"][department] = {}
                current = week_data["department"][department].get(metric_name, 0)
                week_data["department"][department][metric_name] = current * (1 + actual_change/100)
                actual_changes["department"][metric_name] = (actual_change, uncertainty_used)
                
        week_data["changes"] = actual_changes
        self._save_metrics_data()
        return actual_changes
        
    def validate_changes(self, changes: Dict[str, float], department: str) -> bool:
        for metric, change in changes.items():
            category, metric_name = metric.split('.')
            constraints = self.get_metric_constraints(category, department if category == "department" else None)
            
            if metric_name in constraints:
                min_change = constraints[metric_name]["min_change"]
                max_change = constraints[metric_name]["max_change"]
                uncertainty = constraints[metric_name].get("uncertainty_range", 0)
                
                if not (min_change <= change - uncertainty and change + uncertainty <= max_change):
                    print(f"Warning: Change for {metric} ({change}% ± {uncertainty}%) outside allowed range [{min_change}%, {max_change}%]")
                    return False
            else:
                print(f"Warning: Unknown metric {metric}")
                return False
                
        return True
        
    def get_allowed_metrics(self, department: str) -> Dict[str, Dict[str, Dict[str, float]]]:
        return {
            "core": self.get_metric_constraints("core"),
            "department": self.get_metric_constraints("department", department)
        }
