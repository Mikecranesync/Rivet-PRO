import json

# Load the workflow
with open('n8n/workflows/test/rivet_url_validator.json', 'r', encoding='utf-8') as f:
    workflow = json.load(f)

# Fix all Code nodes - change return format from array to object
for node in workflow['nodes']:
    if node.get('type') == 'n8n-nodes-base.code':
        js_code = node.get('parameters', {}).get('jsCode', '')

        # Replace array return with object return
        # Pattern: return [{ json: {...} }]; -> return { json: {...} };
        if 'return [{' in js_code and js_code.strip().endswith('}];'):
            # Remove the array brackets
            js_code = js_code.replace('return [{', 'return {')
            js_code = js_code.rstrip(';').rstrip(']').rstrip() + ';'

            node['parameters']['jsCode'] = js_code
            print(f"Fixed node: {node.get('name')}")

# Save the fixed workflow
with open('n8n/workflows/test/rivet_url_validator_fixed.json', 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2)

print("\n[SAVED] Fixed workflow saved to: n8n/workflows/test/rivet_url_validator_fixed.json")
print("\nReview the changes, then run upload script to push to n8n cloud.")
