import json
import re
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
import os

class RecommendationTracker:
    """Track and manage recommendations from AI agents"""
    
    def __init__(self):
        self.messages = []
        self.decisions = {}
        load_dotenv()
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # define available metrics
        self.metrics = {
            "core": ["revenue", "profit_margin", "customer_satisfaction", "employee_satisfaction"],
            "department": ["sales_growth", "operational_efficiency", "innovation_index", "market_share"],
            "research_and_development": ["research_budget", "development_speed", "innovation_rate"]
        }

    def extract_recommendations_with_gpt(self, content: str) -> Dict[str, float]:
        """Use GPT to extract metric recommendations from agent message"""
        metric_list = []
        for category, metrics in self.metrics.items():
            for metric in metrics:
                metric_list.append(f"{category}.{metric}")
        
        prompt = f"""
        Extract numerical recommendations from the following message. 
        Only extract metrics that have a specific percentage change mentioned.
        Available metrics are: {', '.join(metric_list)}
        
        Message:
        {content}
        
        Format your response as a JSON object where:
        - Keys are metric names in format "category.metric_name"
        - Values are the percentage changes as numbers (without % symbol)
        - Only include metrics that have explicit percentage changes
        
        Example format:
        {{
            "core.revenue": 15,
            "department.operational_efficiency": -5
        }}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            recommendations_str = response.choices[0].message.content.strip()
            try:
                return json.loads(recommendations_str)
            except json.JSONDecodeError:
                print(f"Error parsing GPT response: {recommendations_str}")
                return {}
                
        except Exception as e:
            print(f"Error calling GPT API: {str(e)}")
            return {}

    def process_message(self, sender: str, content: str):
        """Process a message and extract metric recommendations using GPT"""
        self.messages.append({
            "agent": sender,
            "content": content
        })
        
        recommendations = self.extract_recommendations_with_gpt(content)
        
        # store recommendations for this agent
        if recommendations:
            self.decisions[sender] = recommendations
    
    def save_conversation(self, filename: str):
        """Save the entire conversation to a file"""
        with open(filename, 'w') as f:
            for msg in self.messages:
                f.write(f"\n{msg['agent']}:\n{msg['content']}\n")  
                f.write("-" * 50 + "\n")
    
    def save_final_report(self, filename: str):
        """Save the final recommendations to a report file"""
        with open(filename, 'w') as f:
            f.write("=== Final Implementation Report ===\n\n")
            for agent, recommendations in self.decisions.items():
                if recommendations:
                    f.write(f"\n{agent}'s Approved Recommendations:\n")
                    for metric, value in recommendations.items():
                        f.write(f"    - {metric}: {value}%\n")
            f.write("\n" + "=" * 50 + "\n")
