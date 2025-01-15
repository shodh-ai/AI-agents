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
model_client = OpenAIChatCompletionClient(
    api_key="",
    model="gpt-4",
    temperature=0.7,
    timeout=60.0,  # Increase timeout to 60 seconds
    max_retries=3  # Add retries
)

def process_decision(message: str) -> Dict:
    updates = {}
    metrics = {
        "revenue_growth": r"revenue growth.*?(\d+\.?\d*)%",
        "market_share": r"market share.*?(\d+\.?\d*)%",
        "growth_rate": r"growth rate.*?(\d+\.?\d*)%",
        "profit_margin": r"profit margin.*?(\d+\.?\d*)%",
        "customer_acquisition": r"customer acquisition.*?(\d+\.?\d*)%",
        "operational_efficiency": r"operational efficiency.*?(\d+\.?\d*)%"
    }
    
    for metric, pattern in metrics.items():
        match = re.search(pattern, message.lower())
        if match:
            updates[metric] = float(match.group(1))
    
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
            updates = process_decision(content)
            if updates:
                self.decisions[sender] = updates
                print(f"\nDecisions from {sender}:")
                for metric, value in updates.items():
                    print(f"- {metric}: {value}%")
                
                self.data_manager.update_metrics(agent_name=sender, updates=updates)
                print("\nCompany metrics updated!")

ceo = UserProxyAgent(
    name="CEO",
    description="You are the CEO of the company. You make final decisions and set strategic direction."
)

company_info = ""

manager = AssistantAgent(
    name="Manager",
    model_client=model_client,
    system_message="""You are the Manager responsible for operations and team coordination.
    The company operates in following markets like USA, Europe and asia and has 3 products 
    
    Current company data with financial: """ + json.dumps(data_manager.current_data, indent=2) + """
    
    When making recommendations:
    1. Analyze current metrics
    2. Suggest specific percentage changes
    3. Focus on actionable metrics (kind of vague), we can define this.... 
    budget (limitaation), time management (limitation), project deliverables, employee satisfaction, client satisfaction, share price valuation, feedback 
    
    Always specify numerical targets like:
    - revenue growth: X%
    - market share: X%
    - growth rate: X%
    """
)

analyst = AssistantAgent(
    name="Analyst",
    model_client=model_client,
    system_message="""Take the decision that the manager maade and analyse the data.
    Current company data: """ + json.dumps(data_manager.current_data, indent=2) + """
    
    Your tasks:
    1. Analyze financial metrics
    2. Project growth scenarios
    3. Assess market opportunities
    4. Recommend target numbers
    
    Always provide specific percentages:
    - revenue growth: X%
    - market share: X%
    - growth rate: X%
    """
)

cto = AssistantAgent(
    name="CTO",
    model_client=model_client,
    system_message="""You are the CTO responsible for technical strategy and innovation.
    Current company data: """ + json.dumps(data_manager.current_data, indent=2) + """
    
    Focus on:
    1. Technical efficiency
    2. Innovation metrics
    3. Operational improvements
    4. Technology investments
    
    Provide specific targets:
    - operational efficiency: X%
    - customer acquisition: X%
    - technical growth: X%
    """
)

async def main():
    tracker = ConversationTracker(data_manager)
    termination = TextMentionTermination("APPROVE")
    
    team = RoundRobinGroupChat(
        participants=[manager, analyst, cto, ceo],
        max_turns=5,
    )
    initial_message = """As CEO, I want a comprehensive growth strategy:
    1. Current metrics analysis
    
    Each team member should provide specific numerical recommendations."""
    
    try:
        print("\n=== Starting Team Discussion ===\n")
        print(f"CEO: {initial_message}\n")
        tracker.process_message("CEO", initial_message)
        
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                stream = team.run_stream(task=initial_message)
                async for message in stream:
                    print(message)
                    
                    if hasattr(message, 'source') and hasattr(message, 'content'):
                        tracker.process_message(message.source, message.content)
                    elif isinstance(message, dict) and 'content' in message:
                        sender = message.get("name", message.get("sender", "Unknown"))
                        tracker.process_message(sender, message['content'])
                break  # If successful, exit the retry loop
                
            except (httpx.ConnectTimeout, openai.APITimeoutError) as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    print(f"\nConnection timeout. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    print("\nFailed to connect after multiple retries. Please check your internet connection.")
                    raise
        
        with open('conversation_history.txt', 'w') as f:
            f.write("=== Growth Strategy Discussion ===\n\n")
            for msg in tracker.messages:
                f.write(f"{msg['sender']}: {msg['content']}\n\n")
            
            f.write("\n=== Final Decisions ===\n")
            for agent, decisions in tracker.decisions.items():
                f.write(f"\n{agent}'s Decisions:\n")
                for metric, value in decisions.items():
                    f.write(f"- {metric}: {value}%\n")
        
        print("\nDiscussion saved to conversation_history.txt")
        print("Company metrics updated in current_metrics.json")
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    asyncio.run(main())