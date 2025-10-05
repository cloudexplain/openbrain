import { writable } from 'svelte/store';

export const deepResearchEnabled = writable(false);
export const deepResearchDepth = writable(1);

export interface DepthConfig {
	level: number;
	name: string;
	description: string;
	estimatedTime: string;
	maxConcurrentResearchUnits: number;
	maxResearcherIterations: number;
	maxReactToolCalls: number;
	maxStructuredOutputRetries: number;
}

export const depthConfigs: DepthConfig[] = [
	{
		level: 1,
		name: "Quick",
		description: "Basic research with minimal sources (~5 API calls)",
		estimatedTime: "30 seconds - 1 minute",
		maxConcurrentResearchUnits: 1,
		maxResearcherIterations: 1,
		maxReactToolCalls: 2,
		maxStructuredOutputRetries: 1
	},
	{
		level: 2,
		name: "Standard",
		description: "Moderate research with multiple sources (~10 API calls)",
		estimatedTime: "1-3 minutes",
		maxConcurrentResearchUnits: 1,
		maxResearcherIterations: 2,
		maxReactToolCalls: 3,
		maxStructuredOutputRetries: 2
	},
	{
		level: 3,
		name: "Thorough",
		description: "Comprehensive research with cross-referencing (~20 API calls)",
		estimatedTime: "3-8 minutes",
		maxConcurrentResearchUnits: 2,
		maxResearcherIterations: 2,
		maxReactToolCalls: 4,
		maxStructuredOutputRetries: 2
	},
	{
		level: 4,
		name: "Deep",
		description: "Extensive research with detailed analysis (~30 API calls)",
		estimatedTime: "8-15 minutes",
		maxConcurrentResearchUnits: 2,
		maxResearcherIterations: 3,
		maxReactToolCalls: 5,
		maxStructuredOutputRetries: 3
	},
	{
		level: 5,
		name: "Expert",
		description: "Maximum depth research with exhaustive analysis (~45 API calls)",
		estimatedTime: "15-30 minutes",
		maxConcurrentResearchUnits: 3,
		maxResearcherIterations: 3,
		maxReactToolCalls: 5,
		maxStructuredOutputRetries: 3
	}
];
