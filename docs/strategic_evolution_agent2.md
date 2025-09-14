StrategicEvolutionAgent (SEA)
1. High-Level Purpose
The StrategicEvolutionAgent (SEA) is a specialized, high-level agent within the MindX framework. Its primary function is to act as a "special projects" or "campaign manager" for complex, strategic self-improvement tasks.
Unlike the AGInt (which operates on a continuous cognitive loop) or the BDIAgent (which executes tactical, plan-based goals), the SEA is designed to be called as a tool. When a controlling agent (like the BDIAgent) decides that a goal is too abstract or requires a multi-faceted strategic approach (e.g., "Improve the efficiency of the logging system"), it delegates this entire campaign to the SEA.
The SEA then takes ownership of the objective, creates its own internal strategic plan, executes it, and returns a final summary of the outcome.
2. Architectural Placement
The SEA sits at a lower, more specialized level than the BDI agent that calls it. It functions as a powerful, self-contained tool within the agent hierarchy.
MastermindAgent (Top-Level Orchestration)
    └── AGInt (Core Intelligence & PODA Loop)
        └── BDIAgent (Tactical Goal Execution & Planning)
            └── StrategicEvolutionAgent (SEA) (Complex Campaign Execution Tool)
Use code with caution.
3. Core Responsibilities
Receive Abstract Directives: Accept a high-level goal (e.g., "Analyze the codebase for new tool opportunities") from a superior agent.
Strategic Plan Generation: Use its own LLM instance to generate a high-level, multi-step strategic plan to achieve the given directive. This plan consists of its own unique internal actions.
Internal Plan Orchestration: Utilize its internal PlanManager to execute its strategic plan step-by-step, managing state and data flow between actions.
Delegate Tactical Tasks: Use the CoordinatorAgent as a bridge to delegate concrete, tactical tasks (like running a script to modify a file) to lower-level workers.
System Analysis: Leverage its internal SystemAnalyzerTool to gather data about the system's state, performance, and code structure to inform its decisions.
Evaluate Outcomes: After a tactical task is completed, use its LLM to assess the success and quality of the outcome against the original goal.
Report Campaign Results: Conclude the campaign and return a structured summary, including a final status (SUCCESS/FAILURE) and relevant data, to the agent that called it.
4. Key Components & Dependencies
Component	Purpose
LLMHandlerInterface	An LLM instance dedicated to the SEA for high-level strategic planning and evaluation.
PlanManager	An internal manager that executes the SEA's own strategic plans, not to be confused with the BDI's plans.
SystemAnalyzerTool	A specialized tool used to perform deep analysis of the MindX codebase and operational metrics.
CoordinatorAgent	The central hub used to submit requests for tactical execution (e.g., code modification) to other agents.
BeliefSystem	The shared memory where the SEA can store the results of its actions (e.g., analysis reports, evaluation scores).
PerformanceMonitor	Provides performance data to the SystemAnalyzerTool.
ResourceMonitor	Provides resource usage data to the SystemAnalyzerTool.
5. Operational Flow: The Evolution Campaign
The SEA's main entry point is the run_evolution_campaign method. The process is as follows:
Initiation: The method is called with a campaign_goal_description. A unique run ID for the campaign is generated.
Plan Generation: It calls _generate_strategic_plan, which prompts the LLM with the campaign goal and a list of its available internal actions. The LLM returns a JSON list of strategic actions.
Plan Execution: A Plan object is created and passed to the internal PlanManager. The plan_manager.execute_plan() method begins running the actions sequentially.
Action Dispatch: For each action in the plan, the PlanManager calls the SEA's _dispatch_strategic_action method. This dispatcher routes the action to the appropriate internal handler (_sea_action_*).
Conclusion: Once the PlanManager finishes (either by success or failure), run_evolution_campaign calls _conclude_campaign to log the final results to its history file (sea_campaign_history_...json) and returns the summary to the original caller.
6. Internal Strategic Actions
The SEA's power comes from its unique set of internal, high-level actions that form its strategic plans.
Action Type	Handler	Description
REQUEST_SYSTEM_ANALYSIS	_sea_action_request_system_analysis	Uses the SystemAnalyzerTool to inspect the codebase and system metrics, then saves the findings to the BeliefSystem.
SELECT_IMPROVEMENT_TARGET	_sea_action_select_improvement_target	Reads the analysis from the BeliefSystem, sorts potential improvements by priority, and selects the best one(s) to act on.
FORMULATE_SIA_TASK_GOAL	_sea_action_formulate_sia_task_goal	Takes the selected improvement target and reframes it as a clear, actionable instruction for the lower-level Self-Improvement Agent (SIA).
REQUEST_COORDINATOR_FOR_SIA_EXECUTION	_sea_action_request_coordinator_for_sia_execution	Submits the formulated task to the CoordinatorAgent, effectively requesting that a code modification or other tactical action be performed.
EVALUATE_SIA_OUTCOME	_sea_action_evaluate_sia_outcome	After the Coordinator reports back, this action uses the LLM to review the results (e.g., a code diff) and assess the quality of the work.
7. Configuration
The SEA's behavior can be tweaked via configuration files. Key settings include:
strategic_evolution_agent.{agent_id}.llm.provider: Sets the LLM provider (e.g., "gemini").
strategic_evolution_agent.{agent_id}.llm.model: Sets the specific LLM model to be used for strategic reasoning.
8. Known Limitations & Future Work
Disembodied: The SEA, by itself, cannot directly interact with the file system or execute shell commands. It is entirely dependent on the CoordinatorAgent and its associated worker agents to perform these tactical actions.
Tool Dependency: Its success is highly dependent on the quality and availability of its internal tools, especially the SystemAnalyzerTool.
Path Forward: To unblock the agent's full potential, it must be given tools that allow it to interact with its environment directly. The next logical step is to equip the BDIAgent (and by extension, the entire hierarchy) with a SimpleCoder tool capable of:
Reading files.
Writing and overwriting files.
Executing shell commands to list directories or gather information.
