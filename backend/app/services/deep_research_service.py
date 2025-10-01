
import asyncio
import logging
from langgraph.checkpoint.memory import MemorySaver

from app.deep_research.deep_researcher import deep_researcher_builder

from app.config import get_settings

logger = logging.getLogger(__name__)


class DeepResearchService:
    @staticmethod
    async def run_deep_research(
        query: str,
        max_concurrent_research_units: int = 1,
        max_researcher_iterations: int = 1,
        max_react_tool_calls: int = 1,
        max_structured_output_retries: int = 1
    ) -> str:
        """
        Runs the deep research process for a given query.

        Args:
            query: The research query.
            max_concurrent_research_units: Maximum concurrent research units.
            max_researcher_iterations: Maximum researcher iterations.
            max_react_tool_calls: Maximum react tool calls.
            max_structured_output_retries: Maximum structured output retries.

        Returns:
            The final research report.

        Raises:
            Exception: If the research process fails, with detailed error information.
        """
        try:
            logger.info(f"Starting deep research for query: {query[:100]}...")
            logger.info(f"Research params: units={max_concurrent_research_units}, iterations={max_researcher_iterations}, tool_calls={max_react_tool_calls}")

            settings = get_settings()
            config = {
                "configurable": {
                    "thread_id": "azure_research_patched",

                    # Core settings
                    "max_structured_output_retries": 1,
                    "allow_clarification": False,  # Skip clarification for faster testing
                    "max_concurrent_research_units": 1,  # Number of parallel researchers
                    "search_api": "tavily",  # Use Tavily search API
                    "search_api_key": settings.search_api_key,
                    "max_researcher_iterations": 1,  # Supervisor reflection cycles
                    "max_react_tool_calls": 1,  # Max searches per researcher
                    "azure_openai_endpoint": settings.azure_openai_endpoint,
                    "azure_openai_api_version": settings.azure_openai_api_version,
                    "azure_openai_api_key": settings.azure_openai_api_key,
                    "azure_openai_deployment_name": settings.azure_openai_deployment_name,
                    "summarization_model": f"azure_openai://{settings.azure_mini_deployment_name}",
                    "summarization_model_max_tokens": 8192,

                    "research_model": f"azure_openai://{settings.azure_openai_deployment_name}",
                    "research_model_max_tokens": 8000,

                    "compression_model": f"azure_openai://{settings.azure_openai_deployment_name}",
                    "compression_model_max_tokens": 8000,

                    "final_report_model": f"azure_openai://{settings.azure_openai_deployment_name}",
                    "final_report_model_max_tokens": 12000,

                    "max_concurrent_research_units": max_concurrent_research_units,
                    "max_researcher_iterations": max_researcher_iterations,
                    "max_react_tool_calls": max_react_tool_calls,
                    "max_structured_output_retries": max_structured_output_retries,
                }
            }

            # Compile the graph
            graph = deep_researcher_builder.compile(checkpointer=MemorySaver())

            # Execute the research
            result = await graph.ainvoke(
                { "messages": [{"role": "user", "content": query}] }, config=config
            )

            final_report = result.get("final_report", "No report generated.")

            # If final_report is not a string, try to extract the string content
            if isinstance(final_report, (list, tuple)) and len(final_report) > 0:
                # Try to find the actual report content in the structure
                for item in final_report:
                    if isinstance(item, str) and len(item) > 100:  # Assuming report is long
                        logger.info("Deep research completed successfully")
                        return item

            if isinstance(final_report, str):
                logger.info("Deep research completed successfully")
                return final_report

            logger.warning("Deep research completed but report format unexpected")
            return str(final_report)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Deep research failed: {error_msg}", exc_info=True)

            # Check if it's a rate limit error
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                detailed_error = f"Rate limit exceeded during deep research. This usually happens when making too many API calls in a short time. The research parameters were: {max_concurrent_research_units} concurrent units, {max_researcher_iterations} iterations, {max_react_tool_calls} tool calls per unit. Please try again in a few minutes or use lower depth settings."
            else:
                detailed_error = f"Deep research failed due to an unexpected error: {error_msg}"

            # Re-raise with detailed error for the calling service to handle
            raise Exception(detailed_error) from e

if __name__ == "__main__":
    # This is a simple example of how to run the deep research service.
    # You would typically call run_deep_research from your API layer.
    
    # To run this, you need to have your environment variables set up, for example in a .env file
    # in the backend directory, and then run this file as a module.
    # Example:
    # OPENAI_API_KEY="your_key"
    # TAVILY_API_KEY="your_key"
    #
    # python -m app.services.deep_research_service

    async def main():
        query = "What are the latest advancements in AI in 2024?"
        print(f"Running deep research for query: {query}")
        report = await DeepResearchService.run_deep_research(query)
        print("\n--- Final Report ---")
        print(report)

    asyncio.run(main())
