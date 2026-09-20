"""Simplest possible agent: model + tool loop via OpenRouter.

Env vars:
  OPENROUTER_API_KEY  (required)
  OPENROUTER_MODEL    (required, e.g. openai/gpt-4o-mini)
"""

import json
import os
import sys
import urllib.parse
import urllib.request

API_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_weather(city: str) -> str:
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)
    current = data["current_condition"][0]
    return json.dumps({
        "city": city,
        "temp_c": current["temp_C"],
        "feels_like_c": current["FeelsLikeC"],
        "description": current["weatherDesc"][0]["value"],
        "humidity": current["humidity"],
        "wind_kmph": current["windspeedKmph"],
    })


TOOLS = {
    "get_weather": {
        "fn": get_weather,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name"}
                    },
                    "required": ["city"],
                },
            },
        },
    }
}


def show_context(messages: list, turn: int) -> None:
    """Print the full context window being sent to the model."""
    print(f"\n{'=' * 70}")
    print(f" TURN {turn} — full context window being sent ({len(messages)} messages)")
    print(f"{'=' * 70}")
    for i, m in enumerate(messages):
        print(f"\n--- message[{i}] role={m['role'].upper()} ---")
        if m.get("tool_calls"):
            for call in m["tool_calls"]:
                print(f"  tool_call: {call['function']['name']}"
                      f"({call['function']['arguments']}) id={call['id']}")
        if m.get("tool_call_id"):
            print(f"  tool_call_id: {m['tool_call_id']}")
        if m.get("content"):
            print(f"  content: {m['content']}")


def show_response(response: dict, turn: int) -> None:
    """Print what the model decided, plus token usage."""
    usage = response.get("usage", {})
    message = response["choices"][0]["message"]
    print(f"\n{'-' * 70}")
    print(f" TURN {turn} — model response"
          f" ({usage.get('prompt_tokens', '?')} prompt +"
          f" {usage.get('completion_tokens', '?')} completion tokens)")
    print(f"{'-' * 70}")
    if message.get("tool_calls"):
        for call in message["tool_calls"]:
            print(f"  -> wants to call {call['function']['name']}"
                  f"({call['function']['arguments']})")
    else:
        print(f"  -> final answer:\n{message['content']}")


def call_model(messages: list) -> dict:
    body = json.dumps({
        "model": os.environ["OPENROUTER_MODEL"],
        "messages": messages,
        "tools": [t["schema"] for t in TOOLS.values()],
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def run(question: str, max_turns: int = 5) -> str:
    messages = [
        {"role": "system", "content": "You are a helpful weather assistant. "
                                      "Always use the get_weather tool."},
        {"role": "user", "content": question},
    ]

    for turn in range(1, max_turns + 1):
        show_context(messages, turn)
        response = call_model(messages)
        show_response(response, turn)

        message = response["choices"][0]["message"]
        messages.append(message)

        tool_calls = message.get("tool_calls")
        if not tool_calls:
            return message["content"]

        for call in tool_calls:
            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"])
            result = TOOLS[name]["fn"](**args)
            print(f"\n[tool executed] {name}({args}) -> {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": result,
            })

    return "Max turns reached without a final answer."


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Usage: python agent.py "your question"')
    run(" ".join(sys.argv[1:]))
