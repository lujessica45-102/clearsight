import { createHarness } from "@strands-agents/harness";

const agent = await createHarness();
const result = await agent.invoke("Investigate this weather alert.");
