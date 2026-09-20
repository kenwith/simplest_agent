# simplest_agent

The simplest possible agent: a Python script that calls OpenRouter and runs a
tool-calling loop. No dependencies beyond the standard library.

## Setup

```bash
export OPENROUTER_API_KEY="sk-or-..."          # your OpenRouter key
export OPENROUTER_MODEL="~deepseek/deepseek-v4-flash-latest"   # any model id
```

### About the model id

Use the exact ID from https://openrouter.ai/models — it is **case-sensitive**.
Note that OpenRouter's *alias* IDs begin with a tilde:

| | |
|---|---|
| ❌ `deepseek/deepseek-v4-flash-latest` | `400: not a valid model ID` |
| ✅ `~deepseek/deepseek-v4-flash-latest` | works |

If you get `HTTP Error 400: Bad Request`, the slug is wrong. To list valid
IDs:

```bash
curl -s https://openrouter.ai/api/v1/models | python3 -c \
  "import json,sys; print('\n'.join(m['id'] for m in json.load(sys.stdin)['data']))"
```

## Run

```bash
python agent.py "What's the weather in Tokyo?"
```

The agent calls the real `get_weather` tool (wttr.in, no API key needed), feeds
the result back to the model, and prints the final answer. Add more tools by
editing `TOOLS`.

## How it works

### The context window is an array of messages

The API is stateless — the model has no memory between calls. Every request
sends the whole conversation as a JSON array, and the model re-reads it from
scratch. Your script is the memory: it appends each response and tool result
before calling again.

```json
[
  {"role": "system",    "content": "You are a helpful weather assistant..."},
  {"role": "user",      "content": "What's the weather in Tokyo?"},
  {"role": "assistant", "content": null,
   "tool_calls": [{"id": "call_abc", "function":
     {"name": "get_weather", "arguments": "{\"city\": \"Tokyo\"}"}}]},
  {"role": "tool", "tool_call_id": "call_abc",
   "content": "{\"city\": \"Tokyo\", \"temp_c\": \"24\"}"}
]
```

### Roles

`role` tells the model who "said" each message:

| Role | Who | Purpose |
|------|-----|---------|
| `system` | The app developer | Standing instructions — usually first, optional |
| `user` | The human | The question or request |
| `assistant` | The model | Its previous replies, including tool calls it made |
| `tool` | Your code | Results of tool executions, fed back to the model |

### Turns

A "turn" is **one model call**, not one user prompt. You supply one prompt, but
the agent may need several model calls to answer it. `max_turns` caps the loop
so a model that keeps calling tools without answering can't run forever.

## Verbose output

Each turn prints two blocks: the full context window being sent (every message,
role, and tool call), then the model's response with token usage. Tool
executions print their results inline, so you can watch the context window grow
turn by turn.

## Sample run

Command:

```bash
export OPENROUTER_MODEL="~deepseek/deepseek-v4-flash-latest"
python agent.py "What's the weather in Tokyo?"
```

Output:

```text
======================================================================
 TURN 1 — full context window being sent (2 messages)
======================================================================

--- message[0] role=SYSTEM ---
  content: You are a helpful weather assistant. Always use the get_weather tool.

--- message[1] role=USER ---
  content: What's the weather in Tokyo?

----------------------------------------------------------------------
 TURN 1 — model response (387 prompt + 74 completion tokens)
----------------------------------------------------------------------
  -> wants to call get_weather({"city": "Tokyo"})

[tool executed] get_weather({'city': 'Tokyo'}) -> {"city": "Tokyo", "temp_c": "24", "feels_like_c": "19", "description": "Light rain shower", "humidity": "92", "wind_kmph": "57"}

======================================================================
 TURN 2 — full context window being sent (4 messages)
======================================================================

--- message[0] role=SYSTEM ---
  content: You are a helpful weather assistant. Always use the get_weather tool.

--- message[1] role=USER ---
  content: What's the weather in Tokyo?

--- message[2] role=ASSISTANT ---
  tool_call: get_weather({"city": "Tokyo"}) id=call_0df152a1b5334d96b88a8651

--- message[3] role=TOOL ---
  tool_call_id: call_0df152a1b5334d96b88a8651
  content: {"city": "Tokyo", "temp_c": "24", "feels_like_c": "19", "description": "Light rain shower", "humidity": "92", "wind_kmph": "57"}

----------------------------------------------------------------------
 TURN 2 — model response (519 prompt + 82 completion tokens)
----------------------------------------------------------------------
  -> final answer:
The current weather in Tokyo is a **light rain shower** with a temperature of **24°C** (feels like 19°C). Humidity is high at **92%**, and there's a fairly strong wind at **57 km/h**.

Make sure to grab an umbrella if you're heading out! 🌂
```

### What to notice

- **Turn 1** sends 2 messages (system + user). The model replies with a tool
  call, not an answer — it needs data first.
- Your code runs the tool and **appends two messages**: the assistant's tool
  call, then the `tool` result.
- **Turn 2** resends everything — now 4 messages. With the result in hand, the
  model writes the final answer.
- Prompt tokens grow each turn (387 → 519) because the whole history is resent
  every call. That is the cost of statelessness.
