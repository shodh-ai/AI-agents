from typing import Dict, List, Any, Optional
import json
import re
import os
from dotenv import load_dotenv
from datetime import datetime
import numpy as np
import openai
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from recommendation_tracker import RecommendationTracker
from metrics_manager import MetricsManager

class SimulationManager:
    def __init__(self):
        
        self.metrics_manager = MetricsManager("metrics_data.json")
        self.current_metrics = self.metrics_manager.get_week_metrics(1)
        
        with open('simulation_data.json', 'r') as f:
            self.simulation_data = json.load(f)
        self.current_week = 0
        self.user_decisions = []
        self.weekly_decisions = {}
        self.number_pattern = re.compile(r'(?:[\$£€])?(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?(?:k|K|m|M|b|B)?(?:\s*%)?')
        load_dotenv()
        self.openai_client = None
        self._setup_openai()
        self._setup_agents()
        self.conversation_history = []
        self.discussion_started = False
        self.current_department = self.simulation_data["weekly_challenges"]["week1"]["department"]
        self.is_running = True
        self.awaiting_action = False
        self.total_weeks = len(self.simulation_data["weekly_challenges"])
        self.current_recommendations_version = 1  # track versions of recommendations

    def get_current_metrics(self) -> Dict[str, Any]:
        return self.metrics_manager.get_week_metrics(self.current_week + 1)

    def update_metrics(self, changes: Dict[str, Any]) -> None:
        department = self.current_department
        week = self.current_week + 1
        
        if self.metrics_manager.validate_changes(changes, department):
            actual_changes = self.metrics_manager.update_week_metrics(week, department, changes)
            
            if week in self.weekly_decisions:
                self.weekly_decisions[week]["actual_changes"] = actual_changes
            
            self.current_metrics = self.metrics_manager.get_week_metrics(week)
            print("\nActual changes with uncertainty:")
            for category, metrics in actual_changes.items():
                print(f"\n{category.upper()} Metrics:")
                for metric, (change, uncertainty) in metrics.items():
                    print(f"  - {metric}: {change:+.1f}% ± {uncertainty}%")
                    
    def _setup_openai(self):
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                print("Warning: OPENAI_API_KEY not found in environment variables")
                return
            
            self.openai_client = openai.OpenAI(api_key=api_key)
        except Exception as e:
            print(f"Error setting up OpenAI client: {str(e)}")
            
    def _setup_agents(self):
        model_client = OpenAIChatCompletionClient(model="gpt-4")
        
        self.agents = {
            "CEO": AssistantAgent(
                name="CEO",
                model_client=model_client,
                system_message="""You are the CEO, focused on strategic alignment and long-term impact.
                Analyze decisions based on:
                1. Strategic alignment with company goals
                2. Long-term market positioning
                3. Resource allocation efficiency"""
            ),
            "CTO": AssistantAgent(
                name="CTO",
                model_client=model_client,
                system_message="""You are the CTO, focused on technical excellence and innovation.
                Analyze decisions based on:
                1. Technical feasibility and scalability
                2. Innovation potential
                3. Implementation risks and timeline"""
            ),
            "CFO": AssistantAgent(
                name="CFO",
                model_client=model_client,
                system_message="""You are the CFO, focused on financial planning and metrics.
                Analyze decisions based on:
                1. Financial impact and ROI
                2. Budget allocation
                3. Risk management"""
            ),
            "CMO": AssistantAgent(
                name="CMO",
                model_client=model_client,
                system_message="""You are the CMO, focused on marketing and growth.
                Analyze decisions based on:
                1. Market impact and positioning
                2. Customer acquisition and retention
                3. Brand value"""
            ),
            "COO": AssistantAgent(
                name="COO",
                model_client=model_client,
                system_message="""You are the COO, focused on operations and execution.
                Analyze decisions based on:
                1. Operational efficiency
                2. Process optimization
                3. Resource management"""
            ),
            "CHRO": AssistantAgent(
                name="CHRO",
                model_client=model_client,
                system_message="""You are the CHRO, focused on talent and culture.
                Analyze decisions based on:
                1. Team structure and capabilities
                2. Employee development
                3. Cultural impact"""
            ),
            "Sales": AssistantAgent(
                name="Sales",
                model_client=model_client,
                system_message="""You are the Sales, focused on sales and growth.
                Analyze decisions based on:
                1. Sales impact and positioning
                2. Customer acquisition and retention
                3. Sales value"""
            ),
            "Marketing": AssistantAgent(
                name="Marketing",
                model_client=model_client,
                system_message="""You are the Marketing, focused on marketing and growth.
                Analyze decisions based on:
                1. Market impact and positioning
                2. Customer acquisition and retention
                3. Brand value"""
            ),
            "HR": AssistantAgent(
                name="HR",
                model_client=model_client,
                system_message="""You are the HR, focused on talent and culture.
                Analyze decisions based on:
                1. Team structure and capabilities
                2. Employee development
                3. Cultural impact"""
            )
        }
        
        self.user_proxy = UserProxyAgent(
            name="user_proxy"
        )
        self.termination = TextMentionTermination("APPROVE")

    def _is_gpt_available(self) -> bool:
        return self.openai_client is not None

    def _normalize_number(self, value: str) -> float:
        value = value.strip().lower()
        multiplier = 1
        
        if 'k' in value:
            multiplier = 1000
            value = value.replace('k', '')
        elif 'm' in value:
            multiplier = 1000000
            value = value.replace('m', '')
        elif 'b' in value:
            multiplier = 1000000000
            value = value.replace('b', '')
            
        value = value.replace('$', '').replace('£', '').replace('€', '').replace(',', '')
        if '%' in value:
            value = value.replace('%', '')
            multiplier = 0.01
            
        try:
            return float(value) * multiplier
        except ValueError:
            return 0.0

    def _extract_metrics_gpt(self, text: str) -> Dict[str, float]:
        if not self._is_gpt_available():
            return self._extract_metrics_regex(text)
            
        try:
            prompt = f"""Extract the following metrics from the text. Return ONLY a JSON object with these keys:
            - revenue (in dollars)
            - growth (as decimal, e.g., 0.2 for 20%)
            - market_share (as decimal)
            - marketing_budget (in dollars)
            - r_and_d_budget (in dollars)
            - hiring_budget (in dollars)

            If a metric is not found, use 0. Convert all numbers to raw form (e.g., 1M = 1000000).

            Text to analyze:
            {text}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "You are a financial metrics extraction system. Extract metrics and return them in JSON format."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0
            )
            
            metrics = json.loads(response.choices[0].message.content)
            return metrics
            
        except Exception as e:
            print(f"Warning: GPT API error, falling back to regex: {str(e)}")
            return self._extract_metrics_regex(text)
            
    def _extract_metrics_regex(self, text: str) -> Dict[str, float]:
        metrics = {
            'revenue': 0,
            'growth': 0,
            'market_share': 0,
            'marketing_budget': 0,
            'r_and_d_budget': 0,
            'hiring_budget': 0
        }
        
        for line in text.lower().split('\n'):
            if 'revenue' in line:
                nums = self.number_pattern.findall(line)
                if nums: metrics['revenue'] = self._normalize_number(nums[0])
            if 'growth' in line:
                nums = self.number_pattern.findall(line)
                if nums: metrics['growth'] = self._normalize_number(nums[0])
            if 'market' in line and 'share' in line:
                nums = self.number_pattern.findall(line)
                if nums: metrics['market_share'] = self._normalize_number(nums[0])
            if 'marketing' in line and 'budget' in line:
                nums = self.number_pattern.findall(line)
                if nums: metrics['marketing_budget'] = self._normalize_number(nums[0])
            if 'r&d' in line or 'r & d' in line:
                nums = self.number_pattern.findall(line)
                if nums: metrics['r_and_d_budget'] = self._normalize_number(nums[0])
            if 'hiring' in line and 'budget' in line:
                nums = self.number_pattern.findall(line)
                if nums: metrics['hiring_budget'] = self._normalize_number(nums[0])
        
        return metrics

    def _analyze_plan_alignment_gpt(self, user_plan: str, ceo_plan: Dict) -> Dict[str, float]:
        if not self._is_gpt_available():
            return {
                'strategic_alignment': 0.7,
                'initiative_coverage': 0.7,
                'risk_assessment': 0.7,
                'resource_allocation': 0.7,
                'timeline_feasibility': 0.7
            }
            
        try:
            prompt = f"""Analyze how well the user's execution plan aligns with the CEO's objectives.
            Compare these aspects and return ONLY a JSON object with these scores (0.0 to 1.0):
            - strategic_alignment: How well the overall strategy aligns
            - initiative_coverage: How well it covers the key initiatives
            - risk_assessment: How well risks are addressed
            - resource_allocation: How well resources are distributed
            - timeline_feasibility: How realistic the timeline is

            CEO's Objectives:
            {json.dumps(ceo_plan, indent=2)}

            User's Plan:
            {user_plan}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "You are a business strategy analyzer. Evaluate plan alignment and return scores in JSON format."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0
            )
            
            alignment_scores = json.loads(response.choices[0].message.content)
            return alignment_scores
            
        except Exception as e:
            print(f"Warning: GPT API error in alignment analysis: {str(e)}")
            return {
                'strategic_alignment': 0.7,
                'initiative_coverage': 0.7,
                'risk_assessment': 0.7,
                'resource_allocation': 0.7,
                'timeline_feasibility': 0.7
            }

    async def analyze_user_decision_api(
        self, 
        decision: str, 
        department: str = None,
        feedback: str = None,
        specific_recommendations: List[str] = None
    ) -> Dict[str, Any]:
        """API-specific version that returns analysis without waiting for user input"""
        try:
            if not decision.strip():
                return {"error": "No decision provided"}
            
            self.discussion_started = True
            department = department or self.current_department
            if not department:
                return {"error": "Department not specified"}
            
            week_num = self.current_week + 1
            self.current_recommendations_version += 1  # increment version for new analysis
            
            self.weekly_decisions[week_num] = {
                "decision": decision, 
                "recommendations": None,
                "recommendations_version": self.current_recommendations_version,
                "feedback": feedback,
                "specific_recommendations": specific_recommendations
            }
            
            tracker = RecommendationTracker()
            
            dept_to_agent = {
                "PRODUCT": ["CTO", "COO"],
                "SALES": ["Sales", "COO"],
                "MARKETING": ["Marketing", "COO"],
                "HR": ["HR", "COO"],
                "FINANCE": ["CFO", "COO"]
            }
            
            relevant_agents = [self.agents["CEO"]]
            for agent_name in dept_to_agent.get(department.upper(), []):
                if agent_name in self.agents:
                    relevant_agents.append(self.agents[agent_name])
            
            if not relevant_agents:
                return {"error": f"No agents found for department: {department}"}
            
            if feedback and specific_recommendations:
                initial_prompt = f"""
                Department: {department}
                User's Decision: {decision}
                
                User's Feedback on Previous Recommendations:
                {feedback}
                
                Specific Recommendations to Address:
                {chr(10).join(f'- {rec}' for rec in specific_recommendations)}
                
                Provide updated analysis focusing on these specific points. Consider:
                1. How to address the user's feedback
                2. Impact on core metrics (revenue, profit margin, satisfaction)
                3. Impact on department metrics (efficiency, growth, innovation)
                4. Modified implementation steps
                
                Format your response with:
                FEEDBACK RESPONSE:
                - [Point-by-point response to user's concerns]
                
                UPDATED RECOMMENDATIONS:
                - [Modified recommendations]
                
                METRIC ADJUSTMENTS:
                - [Metric Name]: [+/-X%] (with justification)
                
                IMPLEMENTATION STEPS:
                1. [Step 1]
                2. [Step 2]
                ...
                
                RISKS AND MITIGATION:
                - [Risk]: [Mitigation Strategy]
                """
            else:
                initial_prompt = f"""
                Department: {department}
                User's Decision: {decision}
                
                Analyze this decision and provide specific recommendations. Focus on:
                1. Impact on core metrics (revenue, profit margin, satisfaction)
                2. Impact on department metrics (efficiency, growth, innovation)
                3. Implementation steps and timeline
                
                Format your response with:
                METRIC ADJUSTMENTS:
                - [Metric Name]: [+/-X%] (with justification)
                
                IMPLEMENTATION STEPS:
                1. [Step 1]
                2. [Step 2]
                ...
                
                RISKS AND MITIGATION:
                - [Risk]: [Mitigation Strategy]
                """
            
            team = RoundRobinGroupChat(
                participants=relevant_agents,
                max_turns=3
            )
            
            messages = []
            stream = team.run_stream(task=initial_prompt)
            async for message in stream:
                if hasattr(message, 'source') and hasattr(message, 'content'):
                    sender = message.source
                    content = message.content
                    tracker.process_message(sender, content)
                    messages.append({
                        "agent": sender,
                        "content": content
                    })
            
            return {
                "discussion": messages,
                "recommendations": tracker.decisions,
                "implementation_strategy": {
                    "steps": [
                        "Update metrics based on approved recommendations",
                        "Monitor impact on core and department KPIs",
                        "Adjust implementation as needed based on feedback"
                    ],
                    "risks": [
                        "Potential resistance to change",
                        "Implementation timeline may need adjustment",
                        "Resource allocation may need optimization"
                    ]
                }
            }
            
        except Exception as e:
            return {"error": str(e)}

    async def analyze_user_decision(self, decision: str, department: str = None) -> Dict[str, Any]:
        try:
            if not decision.strip():
                return {"error": "No decision provided"}
            
            self.discussion_started = True
            department = department or self.current_department
            if not department:
                return {"error": "Department not specified"}
            
            week_num = self.current_week + 1
            self.weekly_decisions[week_num] = {"decision": decision, "recommendations": None}
            
            tracker = RecommendationTracker()
            
            dept_to_agent = {
                "PRODUCT": ["CTO", "COO"],
                "SALES": ["Sales", "COO"],
                "MARKETING": ["Marketing", "COO"],
                "HR": ["HR", "COO"],
                "FINANCE": ["CFO", "COO"]
            }
            
            relevant_agents = [self.agents["CEO"]]
            for agent_name in dept_to_agent.get(department.upper(), []):
                if agent_name in self.agents:
                    relevant_agents.append(self.agents[agent_name])
            
            if not relevant_agents:
                return {"error": f"No agents found for department: {department}"}
            initial_prompt = f"""
            Department: {department}
            User's Decision: {decision}
            
            Analyze this decision and provide specific recommendations. Focus on:
            1. Impact on core metrics (revenue, profit margin, satisfaction)
            2. Impact on department metrics (efficiency, growth, innovation)
            3. Implementation steps and timeline
            
            Format your response with:
            METRIC ADJUSTMENTS:
            - [Metric Name]: [+/-X%] (with justification)
            
            IMPLEMENTATION STEPS:
            1. [Step 1]
            2. [Step 2]
            ...
            
            RISKS AND MITIGATION:
            - [Risk]: [Mitigation Strategy]
            """
            
            team = RoundRobinGroupChat(
                participants=relevant_agents,
                max_turns=3
            )
            
            print("\n\033[1m=== Starting Analysis Discussion ===\033[0m\n")
            print(f"\033[93mCEO: Analyzing decision for {department} department...\033[0m\n")
            tracker.process_message("CEO", initial_prompt)
            
            stream = team.run_stream(task=initial_prompt)
            async for message in stream:
                print(self._format_message(message))
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
                            for metric, value in recs.items():
                                category, metric_name = metric.split('.')
                                if category == "core":
                                    self.update_core_metric(metric_name, value)
                                elif category == "department":
                                    self.update_department_metric(department, metric_name, value)
                                elif category == "research_and_development":
                                    self.update_r_d_metric(metric_name, value)
                    
                    self.weekly_decisions[week_num]["recommendations"] = tracker.decisions
                    
                    tracker.save_final_report(f'implementation_report_week{week_num}.txt')
                    tracker.save_conversation(f'conversation_history_week{week_num}.txt')
                    print(f"\n\033[92mRecommendations for Week {week_num} approved and implemented!\033[0m")
                    print(f"\033[92mFull discussion saved to conversation_history_week{week_num}.txt\033[0m")
                    print(f"\033[92mDetailed report saved to implementation_report_week{week_num}.txt\033[0m")
                    
                    self.current_week += 1
                    next_week = f"week{self.current_week + 1}"
                    if next_week in self.simulation_data["weekly_challenges"]:
                        next_challenge = self.simulation_data["weekly_challenges"][next_week]
                        print(f"\n\033[1m=== Moving to Week {self.current_week + 1} Challenge ===\033[0m")
                        print(f"\nDepartment: {next_challenge['department']}")
                        print(f"Situation: {next_challenge['situation']}")
                        print("\nAvailable Resources:")
                        for resource, value in next_challenge['available_resources'].items():
                            print(f"- {resource}: {value}")
                        print("\nPossible Approaches:")
                        for approach in next_challenge['possible_approaches']:
                            print(f"- {approach}")
                        
                        self.discussion_started = False
                        self.current_department = next_challenge['department']
                        return {
                            "discussion": tracker.messages,
                            "recommendations": tracker.decisions,
                            "implemented": True,
                            "continue_simulation": True,
                            "implementation_strategy": {
                                "steps": [
                                    "Update metrics based on approved recommendations",
                                    "Monitor impact on core and department KPIs",
                                    "Adjust implementation as needed based on feedback"
                                ],
                                "risks": [
                                    "Potential resistance to change",
                                    "Implementation timeline may need adjustment",
                                    "Resource allocation may need optimization"
                                ]
                            }
                        }
                    else:
                        print("\n\033[93mSimulation completed! No more weekly challenges.\033[0m")
                        return {
                            "discussion": tracker.messages,
                            "recommendations": tracker.decisions,
                            "implemented": True,
                            "continue_simulation": False,
                            "implementation_strategy": {
                                "steps": [
                                    "Update metrics based on approved recommendations",
                                    "Monitor impact on core and department KPIs",
                                    "Adjust implementation as needed based on feedback"
                                ],
                                "risks": [
                                    "Potential resistance to change",
                                    "Implementation timeline may need adjustment",
                                    "Resource allocation may need optimization"
                                ]
                            }
                        }
                
                elif choice == "2":
                    feedback = input("\nEnter your feedback or questions about the recommendations: ")
                    discussion_prompt = f"""The user has provided feedback on the recommendations:
                    {feedback}
                    
                    Please address these concerns and adjust your recommendations if needed."""
                    
                    stream = team.run_stream(task=discussion_prompt)
                    async for message in stream:
                        print(self._format_message(message))
                        if hasattr(message, 'source') and hasattr(message, 'content'):
                            sender = message.source
                            content = message.content
                            tracker.process_message(sender, content)
                    
                elif choice == "3":
                    strategy_request = input("\nWhat kind of alternative strategies would you like to explore? ")
                    new_prompt = f"""The user would like to explore alternative strategies:
                    {strategy_request}
                    
                    Please provide new recommendations based on this direction."""
                    
                    stream = team.run_stream(task=new_prompt)
                    async for message in stream:
                        print(self._format_message(message))
                        if hasattr(message, 'source') and hasattr(message, 'content'):
                            sender = message.source
                            content = message.content
                            tracker.process_message(sender, content)
                    
                elif choice == "4":
                    print("\n\033[93mEnding session without implementing recommendations.\033[0m")
                    break
                
                else:
                    print("\n\033[91mInvalid choice. Please try again.\033[0m")
            
            return {
                "discussion": tracker.messages,  
                "recommendations": tracker.decisions,
                "implemented": choice == "1",
                "implementation_strategy": {
                    "steps": [
                        "Update metrics based on approved recommendations",
                        "Monitor impact on core and department KPIs",
                        "Adjust implementation as needed based on feedback"
                    ],
                    "risks": [
                        "Potential resistance to change",
                        "Implementation timeline may need adjustment",
                        "Resource allocation may need optimization"
                    ]
                }
            }
            
        except Exception as e:
            print(f"Error in analyzing decision: {str(e)}")
            return {"error": str(e)}

    def get_current_metrics(self) -> Dict[str, Any]:
        return self.metrics_manager.get_week_metrics(self.current_week + 1)  # convert to 1-based week number
    
    def update_metrics(self, changes: Dict[str, Any]) -> None:
        department = self.current_department
        week = self.current_week + 1
        
        if self.metrics_manager.validate_changes(changes, department):
            actual_changes = self.metrics_manager.update_week_metrics(week, department, changes)
            
            if week in self.weekly_decisions:
                self.weekly_decisions[week]["actual_changes"] = actual_changes
            
            self.current_metrics = self.metrics_manager.get_week_metrics(week)
            
            print("\nActual changes with uncertainty:")
            for category, metrics in actual_changes.items():
                print(f"\n{category.upper()} Metrics:")
                for metric, (change, uncertainty) in metrics.items():
                    print(f"  - {metric}: {change:+.1f}% ± {uncertainty}%")
                    
    def display_metrics(self, week_number: int) -> None:
        current_metrics = self.get_current_metrics()
        
        if not self.conversation_history:
            print("\nCurrent Metrics:")
            print("Core Metrics:")
            for metric, value in current_metrics["core"].items():
                print(f"  - {metric}: {value}")
            return
            
        previous_metrics = self.conversation_history[-1].get("metrics_before", {})
        
        print("\n=== Week", week_number, "Metrics ===")
        print("\nCore Metrics:")
        for metric, value in current_metrics["core"].items():
            previous = previous_metrics.get("core", {}).get(metric, 0)
            change = ((value - previous) / previous * 100) if previous != 0 else 0
            change_symbol = "↑" if change > 0 else "↓" if change < 0 else "→"
            print(f"  - {metric}: {value:.2f} {change_symbol} ({change:+.1f}%)")
        
        print("\nDepartment Metrics:")
        for dept, metrics in current_metrics["department"].items():
            print(f"\n{dept.upper()}:")
            prev_dept = previous_metrics.get("department", {}).get(dept, {})
            for metric, value in metrics.items():
                previous = prev_dept.get(metric, 0)
                change = ((value - previous) / previous * 100) if previous != 0 else 0
                change_symbol = "↑" if change > 0 else "↓" if change < 0 else "→"
                print(f"  - {metric}: {value:.2f} {change_symbol} ({change:+.1f}%)")
    
    async def handle_user_response(self, week: int, response: str) -> Dict[str, Any]:
        try:
            if response == "approve":
                week_data = self.simulation_data["weekly_challenges"].get(f"week{week}")
                if not week_data:
                    return {"error": f"No data found for week {week}"}
                
                department = week_data["department"]
                if not department:
                    return {"error": "Department not specified in week data"}
                
                if week in self.weekly_decisions and self.weekly_decisions[week].get("recommendations"):
                    changes = {}
                    for agent, recs in self.weekly_decisions[week]["recommendations"].items():
                        for metric, value in recs.items():
                            if metric in changes:
                                changes[metric] = (changes[metric] + value) / 2
                            else:
                                changes[metric] = value
                    self.update_metrics(changes)
                
                return {
                    "status": "approved",
                    "continue_simulation": week < len(self.simulation_data["weekly_challenges"])
                }
            
            return {"error": "Invalid response"}
            
        except Exception as e:
            return {"error": f"Error in handling response: {str(e)}"}

    def update_core_metric(self, metric: str, value: float) -> None:
        if metric in self.current_metrics["core"]:
            current_value = self.current_metrics["core"][metric]
            change = (value / 100.0) * current_value
            self.current_metrics["core"][metric] += change
            
    def update_department_metric(self, department: str, metric: str, value: float) -> None:
        if department.upper() in self.current_metrics["department"] and metric in self.current_metrics["department"][department.upper()]:
            current_value = self.current_metrics["department"][department.upper()][metric]
            change = (value / 100.0) * current_value
            self.current_metrics["department"][department.upper()][metric] += change
            
    def update_r_d_metric(self, metric: str, value: float) -> None:
        if metric in self.current_metrics["research_and_development"]:
            current_value = self.current_metrics["research_and_development"][metric]
            change = (value / 100.0) * current_value
            self.current_metrics["research_and_development"][metric] += change

    def update_resources(self, resources: Dict[str, Any]) -> None:
        for resource, amount in resources.items():
            if resource in self.current_metrics["core"]:
                self.current_metrics["core"][resource] += amount

    def _format_message(self, message) -> str:
        if hasattr(message, 'source') and hasattr(message, 'content'):
            colors = {
                "CEO": "\033[95m",  # Purple
                "CTO": "\033[94m",  # Blue
                "COO": "\033[92m",  # Green
                "CFO": "\033[93m",  # Yellow
                "CMO": "\033[96m",  # Cyan
                "CHRO": "\033[91m", # Red
                "Sales": "\033[91m", # Red
                "Marketing": "\033[96m",  # Cyan
                "HR": "\033[91m", # Red
            }
            
            color = colors.get(message.source, "\033[97m")
            reset = "\033[0m"
            
            return f"{color}{message.source}: {message.content}{reset}\n"
        return str(message)

    def get_weekly_summary(self) -> Dict[str, Any]:
        summary = {}
        for week, data in self.weekly_decisions.items():
            summary[f"Week {week}"] = {
                "Department": self.simulation_data["weekly_challenges"][f"week{week}"]["department"],
                "Situation": self.simulation_data["weekly_challenges"][f"week{week}"]["situation"],
                "Decision": data["decision"],
                "Recommendations": data["recommendations"]
            }
        return summary

    def advance_week(self) -> Dict[str, Any]:
        """Advance the simulation to the next week and return the new state"""
        if not self.is_running:
            return {"error": "Simulation is not running"}
            
        if self.awaiting_action:
            return {"error": "Cannot advance week while awaiting action on current decision"}
            
        if self.current_week >= self.total_weeks - 1:
            self.is_running = False
            return {
                "status": "completed",
                "message": "Simulation has completed all weeks",
                "final_metrics": self.get_current_metrics(),
                "current_week": self.current_week + 1
            }
        
        # apply recommended changes to metrics
        week_num = self.current_week + 1
        if week_num in self.weekly_decisions:
            decision = self.weekly_decisions[week_num]
            if 'recommendations' in decision and decision['recommendations']:
                try:
                    # extract metric changes from recommendations
                    changes = {}
                    for rec in decision['recommendations'].get('metric_impacts', []):
                        if 'metric' in rec and 'change' in rec:
                            changes[rec['metric']] = float(rec['change'])
                    
                    # apply changes through metrics manager
                    if changes:
                        department = self.current_department
                        if self.metrics_manager.validate_changes(changes, department):
                            actual_changes = self.metrics_manager.update_week_metrics(
                                week_num, 
                                department, 
                                changes
                            )
                            print(f"Applied metric changes for week {week_num}: {actual_changes}")
                        else:
                            print(f"Warning: Invalid metric changes for week {week_num}")
                except Exception as e:
                    print(f"Error applying metric changes: {str(e)}")
            
            print(f"Implementing recommendations version {decision.get('recommendations_version', 1)} for week {week_num}")
            
        self.current_week += 1
        self.current_recommendations_version = 1  # reset version for new week
        next_week_metrics = self.get_current_metrics()
        next_challenge = self.get_current_challenge()
        
        return {
            "status": "in_progress",
            "current_week": self.current_week + 1,
            "metrics": next_week_metrics,
            "next_challenge": next_challenge
        }
        
    def get_current_challenge(self) -> Dict[str, Any]:
        """Get the challenge for the current week"""
        week_key = f"week{self.current_week + 1}"
        return self.simulation_data["weekly_challenges"].get(week_key, {})
