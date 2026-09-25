"""
Project P7: ReAct Autonomous Agent Execution Engine
"""
import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AgentStep:
    thought: str
    tool_name: str | None
    tool_args: dict[str, Any] | None
    observation: str | None


@dataclass
class AgentOutcome:
    answer: str
    steps: list[AgentStep]
    success: bool
    iterations: int


class PlatformAgent:
    """Autonomous ReAct agent with tool execution and loop guardrails."""

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.tools: dict[str, Callable[..., str]] = {
            "calculator": self._tool_calculator,
            "knowledge_search": self._tool_knowledge,
        }

    def _tool_calculator(self, expression: str) -> str:
        try:
            return json.dumps({"result": eval(expression, {"__builtins__": {}})})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _tool_knowledge(self, query: str) -> str:
        return json.dumps({"info": f"Knowledge base snippet regarding '{query}'"})

    def execute_task(self, prompt: str) -> AgentOutcome:
        history: list[AgentStep] = []
        action_history: list[str] = []

        for step_i in range(1, self.max_iterations + 1):
            # Step 1: Decision
            if "calculate" in prompt.lower() and step_i == 1:
                thought = "User wants a math calculation."
                tool = "calculator"
                args = {"expression": "120 * 4"}
            elif "search" in prompt.lower() and step_i == 1:
                thought = "User wants knowledge base search."
                tool = "knowledge_search"
                args = {"query": prompt}
            else:
                # Terminal step
                final_step = AgentStep(thought=f"Task complete. Responded to: {prompt}", tool_name=None, tool_args=None, observation=None)
                history.append(final_step)
                return AgentOutcome(
                    answer=final_step.thought,
                    steps=history,
                    success=True,
                    iterations=step_i,
                )

            # Cycle detection
            action_sig = f"{tool}:{json.dumps(args)}"
            if action_history.count(action_sig) >= 2:
                return AgentOutcome(answer="Aborted due to cyclic loop", steps=history, success=False, iterations=step_i)
            action_history.append(action_sig)

            # Execute tool
            fn = self.tools.get(tool)
            obs = fn(**args) if fn else json.dumps({"error": "Tool not found"})
            history.append(AgentStep(thought=thought, tool_name=tool, tool_args=args, observation=obs))

        return AgentOutcome(answer="Exceeded maximum iterations", steps=history, success=False, iterations=self.max_iterations)


platform_agent = PlatformAgent()
