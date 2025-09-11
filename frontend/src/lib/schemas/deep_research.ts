import type { Optional } from '@sveltejs/kit';

export interface DeepResearchRequest {
    query: string;
    chat_id?: Optional<string>;
    max_concurrent_research_units?: Optional<number>;
    max_researcher_iterations?: Optional<number>;
    max_react_tool_calls?: Optional<number>;
    max_structured_output_retries?: Optional<number>;
}

export interface DeepResearchResponse {
    report: string;
}
