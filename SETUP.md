# Setup

## Required
1. `pip install -r requirements.txt`
2. `cp .env.example .env` and add `OPENAI_API_KEY`
3. `streamlit run app.py`

The app runs fully on native tools with just the OpenAI key.

## Optional extras

### Provider swap (Anthropic)
Add `ANTHROPIC_API_KEY` to `.env`. The provider dropdown then runs the app on
Claude with no other change.

### LangSmith (observability)
1. Free account at smith.langchain.com → create an API key
2. In `.env`:
   ```
   LANGSMITH_API_KEY=ls-your-key
   LANGSMITH_TRACING=true
   LANGSMITH_PROJECT=langchain-testing-mastery
   ```
3. Run the app and chat — every step is traced in the LangSmith UI.

### Weather tool
Add `OPENWEATHER_API_KEY` to `.env` (openweathermap.org). Without it, the weather
tool returns a friendly placeholder.

### Live MCP servers (optional, advanced)
Loads your MCP servers as LangChain tools via `langchain-mcp-adapters`.
1. Edit `config/mcp_servers.json` — add server entries (command + args + stdio).
   An example (commented) points at the MCP repo's qa server.
2. In the app sidebar, toggle **Connect live MCP servers**.
Keep it off for a clean first demo; turn it on to show "your old work plugs in."
