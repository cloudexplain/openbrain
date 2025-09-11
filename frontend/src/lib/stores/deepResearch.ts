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
		description: "Basic research with minimal sources",
		estimatedTime: "30 seconds - 2 minutes",
		maxConcurrentResearchUnits: 1,
		maxResearcherIterations: 1,
		maxReactToolCalls: 3,
		maxStructuredOutputRetries: 1
	},
	{
		level: 2,
		name: "Standard",
		description: "Moderate research with multiple sources",
		estimatedTime: "2-5 minutes",
		maxConcurrentResearchUnits: 2,
		maxResearcherIterations: 2,
		maxReactToolCalls: 5,
		maxStructuredOutputRetries: 2
	},
	{
		level: 3,
		name: "Thorough",
		description: "Comprehensive research with cross-referencing",
		estimatedTime: "5-10 minutes",
		maxConcurrentResearchUnits: 3,
		maxResearcherIterations: 3,
		maxReactToolCalls: 8,
		maxStructuredOutputRetries: 3
	},
	{
		level: 4,
		name: "Deep",
		description: "Extensive research with detailed analysis",
		estimatedTime: "10-30 minutes",
		maxConcurrentResearchUnits: 4,
		maxResearcherIterations: 4,
		maxReactToolCalls: 12,
		maxStructuredOutputRetries: 4
	},
	{
		level: 5,
		name: "Expert",
		description: "Maximum depth research with exhaustive analysis",
		estimatedTime: "30 minutes - 1 hour",
		maxConcurrentResearchUnits: 5,
		maxResearcherIterations: 6,
		maxReactToolCalls: 15,
		maxStructuredOutputRetries: 5
	}
];
