from strands import Agent
from strands.models.bedrock import BedrockModel

# Configure the Bedrock model using your specific inference profile ARN
model = BedrockModel(
    model_id="arn:aws:bedrock:us-east-2:473009222412:inference-profile/global.anthropic.claude-sonnet-4-6",
    region_name="us-east-2"
)

# Initialize your Strands agent
agent = Agent(
    model=model,
    system_prompt="You are a helpful AI assistant integrated with AWS Bedrock.",
)

if __name__ == "__main__":
    response = agent("Hello! Confirm you are running on Claude Sonnet 4.6.")
    print(response)