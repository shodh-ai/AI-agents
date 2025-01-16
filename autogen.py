import asyncio
import json
import httpx
import openai
from typing import List, Dict
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from data_manager import DataManager
import re

data_manager = DataManager('company_data.json')
with open('company_info.json', 'r') as f:
    company_info = json.load(f)

company_context = f"""
Company: {company_info['company']['name']} ({company_info['company']['description']})
Products: 
- FlowAI: {company_info['products']['FlowAI']['description']} ({company_info['products']['FlowAI']['users']} users)
- DataSense: {company_info['products']['DataSense']['description']} ({company_info['products']['DataSense']['users']} users)
- IntegrateHub: {company_info['products']['IntegrateHub']['description']} ({company_info['products']['IntegrateHub']['users']} users)

Market Position:
- Total Addressable Market: {company_info['market']['total_addressable_market']}
- Key Segments: SMB ({company_info['market']['current_segments']['small_business']}), Mid-Market ({company_info['market']['current_segments']['mid_market']}), Enterprise ({company_info['market']['current_segments']['enterprise']})
- Geographic Presence: NA ({company_info['market']['geographical_presence']['north_america']}), EU ({company_info['market']['geographical_presence']['europe']}), APAC ({company_info['market']['geographical_presence']['asia_pacific']})

Current Metrics & Goals:
""" + json.dumps(data_manager.current_data, indent=2)

model_client = OpenAIChatCompletionClient(
    api_key="",
    model="gpt-4",
    temperature=0.7
)

ceo = UserProxyAgent(
    name="CEO",
    description="You are the CEO of TechFlow Solutions. You review and approve/reject recommendations."
)

manager = AssistantAgent(
    name="Manager",
    model_client=model_client,
    system_message=f"""You are the Operations Manager at TechFlow Solutions.

{company_context}

Your role is to recommend changes to operational variables that affect revenue and growth:

Variables You Control:
1. Pricing Strategy:
   - Current Price: ${data_manager.current_data['operational_metrics']['pricing']['current_price']}
   - Competitor Price: ${data_manager.current_data['operational_metrics']['pricing']['competitor_price']}
   - Price Elasticity: {data_manager.current_data['operational_metrics']['pricing']['price_elasticity']}

2. Cost Management:
   - Unit Cost: ${data_manager.current_data['operational_metrics']['costs']['unit_cost']}
   - Operational Cost/Employee: ${data_manager.current_data['operational_metrics']['costs']['operational_cost_per_employee']}

Provide recommendations for:
- Price adjustment (%)
- Cost reduction initiatives (%)
- Operational efficiency improvements (%)

Format your recommendations clearly:
"Based on market conditions and operational metrics, I recommend:
- Price adjustment: +/-X%
- Cost reduction: +/-X%
- Operational efficiency: +/-X%"

Explain how these changes will affect revenue and growth rate.
Keep adjustments realistic (under 10% per metric).
"""
)

analyst = AssistantAgent(
    name="Analyst",
    model_client=model_client,
    system_message=f"""You are the Financial Analyst at TechFlow Solutions.

{company_context}

Your role is to recommend workforce and spending changes that affect growth rate:

Variables You Control:
1. Workforce Planning:
   - Current Employees: {data_manager.current_data['operational_metrics']['workforce']['total_employees']}
   - Productivity/Employee: ${data_manager.current_data['operational_metrics']['workforce']['productivity_per_employee']}
   - Hiring Cost/Employee: ${data_manager.current_data['operational_metrics']['workforce']['hiring_cost_per_employee']}

2. Investment Allocation:
   - Marketing Spend: ${data_manager.current_data['operational_metrics']['costs']['marketing_spend']}
   - R&D Spend: ${data_manager.current_data['operational_metrics']['costs']['r_and_d_spend']}

Provide recommendations for:
- Hiring changes (%)
- Marketing spend adjustment (%)
- R&D investment adjustment (%)

Format your recommendations clearly:
"Based on financial analysis, I recommend:
- Hiring change: +/-X%
- Marketing spend: +/-X%
- R&D investment: +/-X%"

Explain how these changes will affect growth rate.
Keep adjustments realistic (under 10% per metric).
"""
)

cto = AssistantAgent(
    name="CTO",
    model_client=model_client,
    system_message=f"""You are the CTO of TechFlow Solutions.

{company_context}

Your role is to recommend partnership and innovation strategies that affect market share:

Variables You Control:
1. Partnerships:
   - Active Partners: {data_manager.current_data['operational_metrics']['partnerships']['active_partners']}
   - Partner Revenue Contribution: {data_manager.current_data['operational_metrics']['partnerships']['partner_contribution_to_revenue'] * 100}%
   - Partnership Cost: ${data_manager.current_data['operational_metrics']['partnerships']['partnership_cost']}

2. Innovation Investment:
   - Current R&D Spend: ${data_manager.current_data['operational_metrics']['costs']['r_and_d_spend']}
   - Engineering Headcount: {data_manager.current_data['operational_metrics']['workforce']['departments']['engineering']}

Provide recommendations for:
- Partnership expansion/optimization (%)
- Technology investment changes (%)
- Innovation initiative adjustments (%)

Format your recommendations clearly:
"Based on technical analysis, I recommend:
- Partnership adjustment: +/-X%
- Tech investment: +/-X%
- Innovation initiatives: +/-X%"

Explain how these changes will affect market share.
Keep adjustments realistic (under 10% per metric).
"""
)

def process_recommendations(message: str) -> Dict:
    updates = {}
    
    # Look for percentage recommendations in various formats
    patterns = {
        'revenue': [
            r'revenue\s*(?:adjustment|change|increase|decrease|growth)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*revenue\s*by\s*([+-]?\d+\.?\d*)%'
        ],
        'growth_rate': [
            r'growth\s*(?:rate)?\s*(?:adjustment|change|increase|decrease)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*growth\s*rate\s*by\s*([+-]?\d+\.?\d*)%'
        ],
        'market_share': [
            r'market\s*share\s*(?:adjustment|change|increase|decrease)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*market\s*share\s*by\s*([+-]?\d+\.?\d*)%'
        ],
        'price_adjustment': [
            r'price\s*(?:adjustment|change|increase|decrease)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*price\s*by\s*([+-]?\d+\.?\d*)%'
        ],
        'cost_reduction': [
            r'cost\s*(?:reduction|change|increase|decrease)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*cost\s*by\s*([+-]?\d+\.?\d*)%'
        ],
        'operational_efficiency': [
            r'operational\s*(?:efficiency|change|increase|decrease)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*operational\s*efficiency\s*by\s*([+-]?\d+\.?\d*)%'
        ],
        'hiring_change': [
            r'hiring\s*(?:change|increase|decrease)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*hiring\s*by\s*([+-]?\d+\.?\d*)%'
        ],
        'marketing_spend_adjustment': [
            r'marketing\s*(?:spend|change|increase|decrease)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*marketing\s*spend\s*by\s*([+-]?\d+\.?\d*)%'
        ],
        'r_and_d_investment_adjustment': [
            r'r\s*&\s*d\s*(?:investment|change|increase|decrease)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*r\s*&\s*d\s*investment\s*by\s*([+-]?\d+\.?\d*)%'
        ],
        'partnership_expansion': [
            r'partnership\s*(?:expansion|change|increase|decrease)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*partnership\s*by\s*([+-]?\d+\.?\d*)%'
        ],
        'technology_investment_change': [
            r'technology\s*(?:investment|change|increase|decrease)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*technology\s*investment\s*by\s*([+-]?\d+\.?\d*)%'
        ],
        'innovation_initiative_adjustment': [
            r'innovation\s*(?:initiative|change|increase|decrease)?\s*:?\s*([+-]?\d+\.?\d*)%',
            r'(?:adjust|change|increase|decrease)\s*innovation\s*initiative\s*by\s*([+-]?\d+\.?\d*)%'
        ]
    }
    
    message = message.lower()
    for metric, patterns_list in patterns.items():
        for pattern in patterns_list:
            match = re.search(pattern, message)
            if match:
                try:
                    value = float(match.group(1))
                    updates[metric] = value
                    break
                except ValueError:
                    continue
    
    return updates

class ConversationTracker:
    def __init__(self, data_manager):
        self.messages = []
        self.decisions = {}
        self.data_manager = data_manager
    
    def process_message(self, sender: str, content: str):
        self.messages.append({
            "sender": sender,
            "content": content,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        if sender in ["Manager", "Analyst", "CTO"]:
            updates = process_recommendations(content)
            if updates:
                self.decisions[sender] = updates
                print(f"\nRecommendations from {sender}:")
                for metric, value in updates.items():
                    print(f"- {metric}: {value}%")

def format_message(message):
    if hasattr(message, 'source') and hasattr(message, 'content'):
        sender = message.source
        content = message.content
        colors = {
            "Manager": "\033[94m",  # blue
            "Analyst": "\033[92m",  # green
            "CTO": "\033[95m",      # purple
            "CEO": "\033[93m"       # yellow
        }
        reset_color = "\033[0m"
        header = f"\n{colors.get(sender, '')}{'-'*20} {sender}'s Recommendation {'-'*20}{reset_color}\n"
        formatted_content = "\n".join("    " + line for line in content.split('\n'))
        
        return f"{header}{formatted_content}\n"
    return str(message)

async def main():
    tracker = ConversationTracker(data_manager)
    
    team = RoundRobinGroupChat(
        participants=[manager, analyst, cto],
        max_turns=3,
    )
    
    initial_message = """As CEO, I need recommendations for our next quarter:
    1. Financial targets and growth projections
    2. Operational improvements
    3. Technology investments
    
    For each metric, provide specific numerical adjustments with clear reasoning.
    Keep recommendations realistic and achievable within a quarter."""
    
    try:
        print("\n\033[1m=== Starting Strategic Planning Session ===\033[0m\n")
        print(f"\033[93mCEO: {initial_message}\033[0m\n")
        tracker.process_message("CEO", initial_message)
        stream = team.run_stream(task=initial_message)
        async for message in stream:
            print(format_message(message))
            if hasattr(message, 'source') and hasattr(message, 'content'):
                sender = message.source
                content = message.content
                tracker.process_message(sender, content)
        
        while True:
            print("\n\033[1m=== Summary of Current Recommendations ===\033[0m")
            for agent, recs in tracker.decisions.items():
                if recs:
                    print(f"\n{agent}'s Recommendations:")
                    for metric, value in recs.items():
                        print(f"    - {metric}: {value}%")
            
            print("\n\033[1mOptions:\033[0m")
            print("1. Accept all recommendations")
            print("2. Discuss specific recommendations")
            print("3. Request new strategies")
            print("4. End session")
            
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == "1":
                for agent, recs in tracker.decisions.items():
                    if recs:
                        data_manager.update_metrics(agent, recs)
                
                data_manager.save_final_report('strategic_planning_report.txt')
                print("\n\033[92mRecommendations approved and implemented!\033[0m")
                print("\033[92mFull discussion saved to conversation_history.txt\033[0m")
                print("\033[92mDetailed report saved to strategic_planning_report.txt\033[0m")
                break
                
            elif choice == "2":
                feedback = input("\nEnter your feedback or questions about the recommendations: ")
                discussion_prompt = f"""The CEO has provided feedback on the recommendations:
                {feedback}
                
                Please address these concerns and adjust your recommendations if needed."""
                
                stream = team.run_stream(task=discussion_prompt)
                async for message in stream:
                    print(format_message(message))
                    if hasattr(message, 'source') and hasattr(message, 'content'):
                        sender = message.source
                        content = message.content
                        tracker.process_message(sender, content)
                
            elif choice == "3":
                strategy_request = input("\nWhat kind of alternative strategies would you like to explore? ")
                new_prompt = f"""The CEO would like to explore alternative strategies:
                {strategy_request}
                
                Please provide new recommendations based on this direction."""
                
                stream = team.run_stream(task=new_prompt)
                async for message in stream:
                    print(format_message(message))
                    if hasattr(message, 'source') and hasattr(message, 'content'):
                        sender = message.source
                        content = message.content
                        tracker.process_message(sender, content)
                
            elif choice == "4":
                print("\n\033[93mEnding session without implementing recommendations.\033[0m")
                break
            
            else:
                print("\n\033[91mInvalid choice. Please try again.\033[0m")
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())