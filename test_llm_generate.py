"""Test LLM Router generate() method"""
import asyncio
from rivet.integrations.llm import LLMRouter, ModelCapability

async def test():
    router = LLMRouter()
    response = await router.generate('What is 2+2?', capability=ModelCapability.SIMPLE)
    print(f'Text generation: {response.text[:50]}...')
    print(f'Model: {response.model}, Cost: ${response.cost_usd:.4f}')

if __name__ == '__main__':
    asyncio.run(test())
