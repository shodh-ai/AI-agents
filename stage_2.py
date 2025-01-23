import os
import json
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, Any

from simulation_manager import SimulationManager

class Message:
    def __init__(self, source: str, content: str):
        self.source = source
        self.name = source
        self.content = content

def display_metrics(simulation: SimulationManager) -> None:
    metrics = simulation.get_current_metrics()
    
    print("\n=== Core Metrics ===")
    if "core" in metrics:
        for metric, value in metrics["core"].items():
            if isinstance(value, (int, float)):
                print(f"{metric}: {value:,.2f}")
            else:
                print(f"{metric}: {value}")
    
    print("\n=== Department Metrics ===")
    if "department" in metrics:
        for dept, dept_metrics in metrics["department"].items():
            print(f"\n{dept}:")
            for metric, value in dept_metrics.items():
                if isinstance(value, (int, float)):
                    print(f"  {metric}: {value:,.2f}")
                else:
                    print(f"  {metric}: {value}")
    
    print("\n=== Research and Development Metrics ===")
    if "research_and_development" in metrics:
        for metric, value in metrics["research_and_development"].items():
            if isinstance(value, (int, float)):
                print(f"{metric}: {value:,.2f}")
            else:
                print(f"{metric}: {value}")
    
    print("\n")

def format_message(msg) -> str:
    if hasattr(msg, 'source'):
        return f"\033[94m{msg.source}: {msg.content}\033[0m"
    return str(msg)

async def main():
    try:
        simulation = SimulationManager()
        
        print("\n\033[1m=== Starting Business Simulation ===\033[0m\n")
        
        while True:
            if not simulation.discussion_started:
                print("\n\033[1m=== Week", simulation.current_week + 1, " Challenge ===\033[0m\n")
                print(f"Department: {simulation.current_department}")
                print(f"Situation: {simulation.simulation_data['weekly_challenges'][f'week{simulation.current_week + 1}']['situation']}\n")
                print("Available Resources:", json.dumps(simulation.simulation_data['weekly_challenges'][f'week{simulation.current_week + 1}']['available_resources'], indent=2))
                print("\nConstraints:", json.dumps(simulation.simulation_data['weekly_challenges'][f'week{simulation.current_week + 1}']['constraints'], indent=2))
                print("\nCurrent Metrics:")
                display_metrics(simulation)
            
            print("\n\033[1mWhat would you like to do?\033[0m")
            print("1. Make a decision")
            print("2. View current metrics")
            print("3. End simulation")
            
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == "1":
                # Get user's decision
                print("\n\033[1mWhat is your decision to address this challenge?\033[0m")
                print("Please describe your approach and key actions.")
                print("Type your response below:")
                print("\n---------- Your Decision ----------")
                decision = input().strip()
                print("--------------------------------")
                
                if not decision:
                    print("\n\033[91mNo decision provided. Please provide a decision to continue.\033[0m")
                    continue
                
                print("\n\033[1m=== Starting AI Analysis ===\033[0m")
                print("The AI agents will analyze your decision and propose an implementation strategy.\n")
                
                analysis_result = await simulation.analyze_user_decision(decision)
                
                if "error" not in analysis_result:
                    for msg in analysis_result["discussion"]:
                        print(format_message(Message(msg["agent"], msg["content"])))
                    
                    strategy = analysis_result.get("implementation_strategy", {})
                    
                    print("\n=== Proposed Implementation Strategy ===")
                    print("\nSteps:")
                    for i, step in enumerate(strategy.get("steps", []), 1):
                        print(f"{i}. {step}")
                    
                    print("\nRisks:")
                    for risk in strategy.get("risks", []):
                        print(f"- {risk}")
                    
                    print("\nExpected Impact:")
                    for category, metrics in strategy.get("impacts", {}).items():
                        if metrics:
                            print(f"\n{category.title()} Metrics:")
                            for metric, value in metrics.items():
                                if isinstance(value, (int, float)):
                                    color = "\033[92m" if value > 0 else "\033[91m" if value < 0 else "\033[0m"
                                    print(f"  - {metric}: {color}{value:+.1f}%\033[0m")
                
                while True:
                    print("\nOptions:")
                    print("1. Accept all recommendations")
                    print("2. Discuss specific recommendations")
                    print("3. Request new strategies")
                    print("4. End session")
                    
                    subchoice = input("\nEnter your choice (1-4): ").strip()
                    if subchoice == "1":
                        print("\n\033[92mImplementing strategy...\033[0m")
                        result = await simulation.handle_user_response(simulation.current_week + 1, "approve")
                        if result.get("error"):
                            print(f"\n\033[91mError: {result['error']}\033[0m")
                            continue
                        
                        if result.get("status") == "approved":
                            print("\n\033[92m✓ Strategy approved and implemented!\033[0m")
                            print("\n\033[1m=== Updated Metrics ===\033[0m")
                            display_metrics(simulation)
                            
                            simulation.current_week += 1
                            if simulation.current_week >= len(simulation.simulation_data["weekly_challenges"]):
                                print("\nSimulation completed! Thank you for participating.")
                                return
                                
                            print(f"\n\033[1m=== Week {simulation.current_week + 1} Challenge ===\033[0m\n")
                            week_data = simulation.simulation_data["weekly_challenges"][f"week{simulation.current_week + 1}"]
                            print(f"Department: {week_data['department']}")
                            print(f"Situation: {week_data['situation']}\n")
                            print("Available Resources:", json.dumps(week_data.get("resources", {}), indent=2))
                            print("\nConstraints:", json.dumps(week_data.get("constraints", {}), indent=2))
                            print("\nCurrent Metrics:")
                            display_metrics(simulation)
                            break
                            
                    elif subchoice == "2":
                        print("\nWhich aspect would you like to discuss?")
                        print("1. Core Metrics Impact")
                        print("2. Department Metrics Impact")
                        print("3. Implementation Timeline")
                        print("4. Back to main options")
                        discuss_choice = input("\nEnter your choice (1-4): ").strip()
                        continue
                        
                    elif subchoice == "3":
                        print("\nRequesting new strategies from AI agents...")
                        break
                        
                    elif subchoice == "4":
                        print("\nEnding simulation. Thank you for participating!")
                        return
                        
                    else:
                        print("\n\033[91mInvalid choice. Please try again.\033[0m")
            
            elif choice == "2":
                display_metrics(simulation)
                input("\nPress Enter to continue...")
            
            elif choice == "3":
                print("\n\033[93mEnding simulation...\033[0m")
                print(f"\nCompleted {simulation.current_week} out of 4 weeks")
                print("\n=== Final Metrics ===")
                display_metrics(simulation)
                print("\n=== Weekly Decisions and Recommendations ===")
                summary = simulation.get_weekly_summary()
                for week, data in summary.items():
                    print(f"\n{week}:")
                    print(f"Department: {data['Department']}")
                    print(f"Situation: {data['Situation']}")
                    print(f"Decision: {data['Decision']}")
                    if data['Recommendations']:
                        print("Recommendations:")
                        for agent, recs in data['Recommendations'].items():
                            print(f"  {agent}:")
                            for metric, value in recs.items():
                                print(f"    - {metric}: {value}%")
                return
            
            else:
                print("\nInvalid choice. Please try again.")

    except Exception as e:
        print(f"\n\033[91mError: {str(e)}\033[0m")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())