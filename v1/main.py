from dotenv import load_dotenv
from agents.orchestrator import orchestrator

load_dotenv()

if __name__ == "__main__":
    question = input("問題：")
    print("\n思考中...\n")
    answer = orchestrator(question)
    print("答案：")
    print(answer)
