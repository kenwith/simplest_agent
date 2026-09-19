# simplest_agent

The simplest possible agent: a Python script that calls OpenRouter and runs a
tool-calling loop. No dependencies beyond the standard library.

## Setup

```bash
export OPENROUTER_API_KEY="sk-or-..."
export OPENROUTER_MODEL="openai/gpt-4o-mini"   # any OpenRouter model id
```

## Run

```bash
python agent.py "What's the weather in Tokyo?"
```

The agent will call the real `get_weather` tool (wttr.in, no API key needed),
feed the result back to the model, and print the final answer. Add more tools
by editing `TOOLS`.

## Verbose output

Each turn prints two blocks: the full context window being sent (every
message, role, and tool call), then the model's response with token usage.
Tool executions print their results inline, so you can watch the context
window grow turn by turn.
