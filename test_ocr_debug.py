"""Debug OCR pipeline in detail"""
import asyncio

async def debug_ocr():
    print("=== OCR Pipeline Debug ===\n")

    # Step 1: Check LLM Router
    print("1. Checking LLM Router...")
    from rivet.integrations.llm import get_llm_router, VISION_PROVIDER_CHAIN

    router = get_llm_router()
    available = router.get_available_providers()

    print(f"   Available providers: {available}")
    print(f"   Vision chain length: {len(VISION_PROVIDER_CHAIN)}")
    print(f"   Vision chain providers:")
    for i, pc in enumerate(VISION_PROVIDER_CHAIN):
        print(f"     {i+1}. {pc.name}/{pc.model} (cost: ${pc.cost_per_1k_input}/1k)")

    # Step 2: Check which providers are in both lists
    print("\n2. Matching providers...")
    for pc in VISION_PROVIDER_CHAIN:
        in_available = "YES" if pc.name in available else "NO"
        print(f"   {pc.name}: In chain? YES | In available? {in_available}")

    # Step 3: Try to call vision directly
    print("\n3. Testing vision call...")
    fake_image = b"TEST IMAGE DATA"

    for pc in VISION_PROVIDER_CHAIN:
        if pc.name not in available:
            print(f"   Skipping {pc.name} (not available)")
            continue

        try:
            print(f"   Trying {pc.name}/{pc.model}...")
            text, cost = await router.call_vision(
                pc,
                fake_image,
                "Describe this image",
                max_tokens=100
            )
            print(f"   SUCCESS! Got response: {len(text)} chars, cost: ${cost}")
            return True
        except Exception as e:
            print(f"   FAILED: {e}")

    print("\n❌ All vision providers failed!")
    return False

if __name__ == "__main__":
    asyncio.run(debug_ocr())
