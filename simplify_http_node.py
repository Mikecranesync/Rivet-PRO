import json

# Load the fixed workflow
with open('n8n/workflows/test/rivet_url_validator_fixed.json', 'r', encoding='utf-8') as f:
    workflow = json.load(f)

# Find the HTTP HEAD Check node and simplify it
for node in workflow['nodes']:
    if node.get('name') == 'HTTP HEAD Check':
        print(f"Current HTTP node config:")
        print(json.dumps(node['parameters'], indent=2))

        # Simplify to minimal configuration
        node['parameters'] = {
            'url': '={{$json.url}}',
            'method': 'HEAD',
            'options': {}
        }

        print(f"\nSimplified HTTP node config:")
        print(json.dumps(node['parameters'], indent=2))

        # Also remove continueOnFail temporarily to see actual errors
        if 'continueOnFail' in node:
            del node['continueOnFail']

# Save
with open('n8n/workflows/test/rivet_url_validator_simplified.json', 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2)

print("\n[SAVED] Simplified workflow saved to: n8n/workflows/test/rivet_url_validator_simplified.json")
