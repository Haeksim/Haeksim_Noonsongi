import asyncio
from agent_lang.agent import get_agent_executor
from langchain_core.messages import HumanMessage

async def main():
    agent_executor = get_agent_executor()
    
    print("🤖 에이전트가 준비되었습니다. 질문을 입력하세요.")
    user_input = input()
    
    response = await agent_executor.ainvoke({
        "messages": [HumanMessage(content=user_input)]
    })
    
    print("\n--- 🤖 에이전트 최종 응답 ---")
    if "messages" in response:
        last_message = response['messages'][-1]
        print(last_message.content)
    elif "output" in response:
        print(response.get("output"))
    else:
        print(f"예상치 못한 응답 형식입니다: {response}")

if __name__ == "__main__":
    asyncio.run(main())