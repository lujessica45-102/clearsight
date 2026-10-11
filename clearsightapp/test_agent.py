from strands import Agent
from strands.models.openai_responses import OpenAIResponsesModel

model = OpenAIResponsesModel(
    model_id="global.openai.gpt-5.6-luna",
    bedrock_mantle_config={
        "endpoint": "bedrock-runtime",
        "region": "us-east-2",
    },
)

agent = Agent(model=model)

print("Calling GPT-5.6 Luna...", flush=True)
response = agent("Say hello in one sentence.")
print(response)
