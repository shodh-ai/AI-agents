import json
from typing import Dict, Any
from copy import deepcopy
import pandas as pd
from datetime import datetime

class DataManager:
    def __init__(self, initial_data_file: str):
        with open(initial_data_file, 'r') as file:
            self.initial_data = json.load(file)
        self.current_data = deepcopy(self.initial_data)
        self.history = []
        
    def update_metrics(self, agent_name: str, updates: Dict[str, Any]) -> None:
        timestamp = datetime.now().isoformat()
        previous_state = deepcopy(self.current_data)
        
        for key, value in updates.items():
            if key in self.current_data['current_metrics']:
                self.current_data['current_metrics'][key] = value
        
        change = {
            'timestamp': timestamp,
            'agent': agent_name,
            'updates': updates,
            'previous_state': previous_state,
            'new_state': deepcopy(self.current_data)
        }
        self.history.append(change)
    
    def calculate_impact(self) -> Dict[str, Any]:
        initial = self.initial_data['current_metrics']
        current = self.current_data['current_metrics']
        
        impact = {}
        for metric, value in current.items():
            if metric in initial:
                if isinstance(value, (int, float)):
                    absolute_change = value - initial[metric]
                    percentage_change = (absolute_change / initial[metric]) * 100 if initial[metric] != 0 else float('inf')
                    impact[metric] = {
                        'initial_value': initial[metric],
                        'final_value': value,
                        'absolute_change': absolute_change,
                        'percentage_change': percentage_change
                    }
        
        return impact
    
    def get_agent_contributions(self) -> pd.DataFrame:
        contributions = []
        
        for change in self.history:
            metrics_impact = {}
            prev = change['previous_state']['current_metrics']
            new = change['new_state']['current_metrics']
            
            for metric in prev:
                if isinstance(prev[metric], (int, float)):
                    absolute_change = new[metric] - prev[metric]
                    percentage_change = (absolute_change / prev[metric]) * 100 if prev[metric] != 0 else float('inf')
                    metrics_impact[f'{metric}_change'] = absolute_change
                    metrics_impact[f'{metric}_change_pct'] = percentage_change
            
            contribution = {
                'timestamp': change['timestamp'],
                'agent': change['agent'],
                **metrics_impact
            }
            contributions.append(contribution)
        
        return pd.DataFrame(contributions)
    
    def save_final_report(self, filename: str) -> None:
        impact = self.calculate_impact()
        
        report = []
        report.append("Company Growth Strategy Impact Report")
        report.append("=================================\n")
        report.append("Overall Impact:")
        report.append("--------------")
        for metric, changes in impact.items():
            report.append(f"{metric}:")
            report.append(f"  Initial Value: {changes['initial_value']}")
            report.append(f"  Final Value: {changes['final_value']}")
            report.append(f"  Absolute Change: {changes['absolute_change']:.2f}")
            report.append(f"  Percentage Change: {changes['percentage_change']:.2f}%\n")
        
        report.append("Agent Contributions:")
        report.append("------------------")
        contributions_df = self.get_agent_contributions()
        report.append(contributions_df.to_string())
        with open(filename, 'w') as f:
            f.write('\n'.join(report))
        
        with open('final_company_data.json', 'w') as f:
            json.dump(self.current_data, f, indent=2)

    def save_metrics(self):
        try:
            with open('current_metrics.json', 'w') as f:
                json.dump(self.current_data, f, indent=2)
            print("Metrics saved to current_metrics.json")
        except Exception as e:
            print(f"Error saving metrics: {str(e)}")
