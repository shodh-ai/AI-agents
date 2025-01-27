import json, os
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv()

def load_context(file_path):
    """Load the context from a JSON file."""
    with open(file_path, 'r') as file:
        return json.load(file)

async def main():
    print("Welcome to the Execution Plan Builder.")

    context_file = "execution_context.json"
    context = load_context(context_file)

    print("\nLoaded Context:")
    print(json.dumps(context, indent=4))

    api_key = os.getenv("APIkey")

    model_client = OpenAIChatCompletionClient(
        model="gpt-4o",
        api_key=api_key
    )
    assistant = AssistantAgent("CEO", model_client=model_client)
    user_proxy = UserProxyAgent("user", input_func=input)

    text_termination = TextMentionTermination("TERMINATE")

    #max_turns set to pause after 10 turns
    team = RoundRobinGroupChat(
        [assistant, user_proxy],
        termination_condition=text_termination,
        max_turns=10
    )

    context_text = json.dumps(context, indent=4)
    task = (
        f"Develop an execution plan based on the provided context. "
        f"The context is as follows:\n{context_text}"
    )
    conversation_history = [task]  # Store conversation history

    while True:
        print("\nRunning conversation with the Assistant Agent...")

        #pass the full conversation history to the team
        stream = team.run_stream(task="\n".join(conversation_history))
        await Console(stream)

        #check for a termination signal from the team
        if hasattr(team, "messages") and any(
            msg.content.strip().lower() == "terminate" for msg in team.messages
        ):
            print("\nFinalizing the plan after reaching the termination condition.")
            break

        #further refinement or finalization
        user_input = input("\nRefine the execution plan or enter 'finalize' to proceed: ").strip()
        if user_input.lower() == 'finalize':
            print("\nProceeding with the current execution plan.")
            break

        #add the user input to the conversation history 
        conversation_history.append(f"User request: {user_input}")
        task = (
            "Based on the provided plan and the user request for refinement, update the execution plan to:\n"
            f"{user_input}"
        )
        conversation_history.append(task)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
