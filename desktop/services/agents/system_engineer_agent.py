"""
System Engineer Agent
Uses multi-LLM provider for high-level reasoning about block graph architecture.
Validates hardware compatibility, pin conflicts, and data flow.
"""

from agents.llm_provider import get_provider


class SystemEngineerAgent:
    """AI agent for system-level architecture reasoning."""

    def __init__(self):
        self.llm = get_provider()

    async def analyze_graph(self, canvas: dict) -> dict:
        """
        Analyze a canvas graph for:
        - Pin conflicts
        - Missing connections
        - Library incompatibilities
        - Power budget issues
        - Data type mismatches between connected ports
        """
        if not self.llm.is_available():
            return {
                "status": "skipped",
                "message": "No LLM provider available",
                "issues": [],
                "suggestions": [],
            }

        prompt = f"""You are an embedded systems architect. Analyze this block graph for an ESP32 project.

Block Graph:
{canvas}

Analyze for:
1. Pin conflicts (two blocks using the same GPIO)
2. Missing connections (blocks with unconnected required inputs)
3. Library incompatibilities
4. Power budget concerns
5. Data type mismatches between connected ports

Respond in JSON format:
{{
    "issues": [
        {{"severity": "error|warning|info", "block_id": "...", "message": "..."}}
    ],
    "suggestions": [
        {{"message": "...", "priority": "high|medium|low"}}
    ],
    "pin_map": {{
        "GPIO_XX": "block_name.function"
    }}
}}"""

        try:
            response = await self.llm.generate(prompt, max_tokens=2000)
            return {
                "status": "analyzed",
                "response": response,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "issues": [],
                "suggestions": [],
            }

    async def suggest_improvements(self, canvas: dict) -> dict:
        """Proactively suggest improvements and additional features."""
        if not self.llm.is_available():
            return {"suggestions": []}

        prompt = f"""You are an embedded systems architect. Given this ESP32 block graph, suggest 
complementary features the user might want to add.

Block Graph:
{canvas}

For example, if they have WiFi, suggest OTA updates. If they have sensors, suggest data logging.
Respond with a JSON array of suggestions, each with "feature", "reason", and "blocks_needed"."""

        try:
            response = await self.llm.generate(prompt, max_tokens=1000)
            return {
                "status": "success",
                "suggestions": response,
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "suggestions": []}
