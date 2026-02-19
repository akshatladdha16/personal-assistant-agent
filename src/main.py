import asyncio

from langchain_core.messages import HumanMessage

from src.agent.graph import graph


async def main():
    print("📚 Resource Librarian Agent CLI (type 'help' for guidance, 'quit' to exit)")
    print("-----------------------------------------------------------------------")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "exit"]:
            break
        if user_input.lower() == "help":
            print(
                "Agent: Try phrases like 'save https://example.com under machine learning' or "
                "'find resources about prompt engineering with tag llm'."
            )
            continue

        # Run the graph
        # We pass a single HumanMessage. The graph state acts as memory
        # (though currently ephemeral without checkpointer).
        inputs = {"messages": [HumanMessage(content=user_input)]}

        # 'stream' allows us to see steps, but for now we just want the final result
        try:
            result = await graph.ainvoke(inputs)
        except Exception as exc:
            print(f"Agent: Something went wrong running the agent: {exc}")
            continue

        # properties of result varies, but with our state it returns the full state
        last_message = result["messages"][-1]
        print(f"Agent: {last_message.content}")


if __name__ == "__main__":
    asyncio.run(main())
