"""
Mermaid Diagram Parser - Convert Mermaid flowchart syntax into navigable tree structure.

Parses Mermaid flowchart diagrams into Python dicts with nodes and edges,
supporting both TD (top-down) and LR (left-right) orientations.

This enables decision tree navigation in Telegram bots where:
- Nodes become steps in a troubleshooting flow
- Edge labels become button text for user choices
- Decision nodes (rhombus) offer multiple paths
- Action nodes (rectangles) provide instructions

Example Mermaid Input:
    flowchart TD
        A[Start] --> B{Is power on?}
        B -->|Yes| C[Check display]
        B -->|No| D[Turn on power]

Example Output:
    {
        "orientation": "TD",
        "nodes": {
            "A": {"id": "A", "label": "Start", "type": "action"},
            "B": {"id": "B", "label": "Is power on?", "type": "decision"},
            "C": {"id": "C", "label": "Check display", "type": "action"},
            "D": {"id": "D", "label": "Turn on power", "type": "action"}
        },
        "edges": [
            {"from": "A", "to": "B", "label": None},
            {"from": "B", "to": "C", "label": "Yes"},
            {"from": "B", "to": "D", "label": "No"}
        ],
        "root": "A"
    }
"""

import re
from typing import Dict, List, Any, Optional, Tuple


def parse_mermaid_flowchart(mermaid_text: str) -> Dict[str, Any]:
    """
    Parse Mermaid flowchart syntax into a navigable tree structure.

    Args:
        mermaid_text: Raw Mermaid flowchart definition

    Returns:
        Dict containing:
            - orientation: "TD" (top-down) or "LR" (left-right)
            - nodes: Dict of node_id -> {id, label, type}
            - edges: List of {from, to, label} dicts
            - root: ID of the root/start node

    Raises:
        ValueError: If the input is not a valid Mermaid flowchart

    Example:
        >>> mermaid = '''
        ... flowchart TD
        ...     A[Start] --> B{Decision?}
        ...     B -->|Yes| C[Action 1]
        ...     B -->|No| D[Action 2]
        ... '''
        >>> result = parse_mermaid_flowchart(mermaid)
        >>> result["orientation"]
        'TD'
        >>> len(result["nodes"])
        4
        >>> result["root"]
        'A'
    """
    lines = mermaid_text.strip().split('\n')

    # Parse header for orientation
    orientation = _parse_orientation(lines)

    # Parse nodes and edges
    nodes = {}
    edges = []

    for line in lines:
        line = line.strip()

        # Skip empty lines and header
        if not line or line.startswith('flowchart') or line.startswith('graph'):
            continue

        # Skip comments
        if line.startswith('%%'):
            continue

        # Skip subgraph definitions for now
        if line.startswith('subgraph') or line == 'end':
            continue

        # Parse edge definitions (lines with arrows)
        if '-->' in line or '---' in line:
            parsed_nodes, parsed_edge = _parse_edge_line(line)

            # Add any nodes found in this line
            for node in parsed_nodes:
                if node["id"] not in nodes:
                    nodes[node["id"]] = node

            if parsed_edge:
                edges.append(parsed_edge)

        # Parse standalone node definitions
        else:
            node = _parse_node_definition(line)
            if node and node["id"] not in nodes:
                nodes[node["id"]] = node

    # Determine root node (first node with no incoming edges)
    root = _find_root_node(nodes, edges)

    return {
        "orientation": orientation,
        "nodes": nodes,
        "edges": edges,
        "root": root
    }


def _parse_orientation(lines: List[str]) -> str:
    """
    Extract flowchart orientation from header line.

    Supports: TD (top-down), TB (top-bottom), LR (left-right),
              RL (right-left), BT (bottom-top)

    Args:
        lines: All lines from the Mermaid definition

    Returns:
        Orientation string, defaults to "TD"

    Example:
        >>> _parse_orientation(["flowchart LR", "  A --> B"])
        'LR'
        >>> _parse_orientation(["graph TD", "  A --> B"])
        'TD'
    """
    for line in lines:
        line = line.strip().lower()
        if line.startswith('flowchart') or line.startswith('graph'):
            # Extract orientation
            parts = line.split()
            if len(parts) >= 2:
                orientation = parts[1].upper()
                if orientation in ('TD', 'TB', 'LR', 'RL', 'BT'):
                    return orientation
    return "TD"  # Default


def _parse_node_definition(text: str) -> Optional[Dict[str, str]]:
    """
    Parse a single node definition.

    Supports:
        - A[Label] - Rectangle (action node)
        - A{Label} - Rhombus (decision node)
        - A(Label) - Rounded rectangle
        - A((Label)) - Circle
        - A>Label] - Flag shape
        - A[[Label]] - Subroutine
        - A[(Label)] - Cylinder
        - A{{Label}} - Hexagon

    Args:
        text: Node definition string

    Returns:
        Dict with id, label, type or None if not a valid node

    Example:
        >>> _parse_node_definition("A[Start Here]")
        {'id': 'A', 'label': 'Start Here', 'type': 'action'}
        >>> _parse_node_definition("B{Is it working?}")
        {'id': 'B', 'label': 'Is it working?', 'type': 'decision'}
    """
    text = text.strip()

    # Skip empty or comment lines
    if not text or text.startswith('%%'):
        return None

    # Pattern for different node shapes
    # Decision nodes: {curly braces}
    decision_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\{([^}]+)\}', text)
    if decision_match:
        return {
            "id": decision_match.group(1),
            "label": decision_match.group(2).strip(),
            "type": "decision"
        }

    # Rectangle nodes: [square brackets]
    rect_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\[([^\]]+)\]', text)
    if rect_match:
        # Check for double brackets [[subroutine]]
        label = rect_match.group(2)
        if label.startswith('[') and label.endswith(']'):
            label = label[1:-1]
        return {
            "id": rect_match.group(1),
            "label": label.strip(),
            "type": "action"
        }

    # Rounded rectangle: (parentheses)
    round_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\(([^)]+)\)', text)
    if round_match:
        # Check for double parens ((circle))
        label = round_match.group(2)
        if label.startswith('(') and label.endswith(')'):
            label = label[1:-1]
            return {
                "id": round_match.group(1),
                "label": label.strip(),
                "type": "terminal"  # Circle typically means start/end
            }
        return {
            "id": round_match.group(1),
            "label": label.strip(),
            "type": "action"
        }

    # Hexagon: {{double curly}}
    hex_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\{\{([^}]+)\}\}', text)
    if hex_match:
        return {
            "id": hex_match.group(1),
            "label": hex_match.group(2).strip(),
            "type": "preparation"
        }

    # Plain node ID (no shape)
    plain_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)$', text)
    if plain_match:
        return {
            "id": plain_match.group(1),
            "label": plain_match.group(1),
            "type": "action"
        }

    return None


def _parse_edge_line(line: str) -> Tuple[List[Dict], Optional[Dict]]:
    """
    Parse a line containing an edge definition.

    Supports:
        - A --> B (simple arrow)
        - A -->|Label| B (arrow with label)
        - A --- B (line without arrow)
        - A ---|Label| B (line with label)
        - A --> B --> C (chained edges)

    Args:
        line: Line containing edge definition

    Returns:
        Tuple of (list of nodes found, edge dict or None)

    Example:
        >>> nodes, edge = _parse_edge_line("A[Start] --> B{Check}")
        >>> len(nodes)
        2
        >>> edge
        {'from': 'A', 'to': 'B', 'label': None}
        >>> nodes, edge = _parse_edge_line("B -->|Yes| C[OK]")
        >>> edge["label"]
        'Yes'
    """
    nodes = []
    edge = None

    # Pattern for edges with optional labels
    # Matches: A -->|Label| B or A --> B
    edge_pattern = re.compile(
        r'([A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\]|\{[^}]*\}|\([^)]*\))?)'  # Source node
        r'\s*'
        r'(-+>+|-+)'  # Arrow type
        r'(?:\|([^|]*)\|)?'  # Optional label
        r'\s*'
        r'([A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\]|\{[^}]*\}|\([^)]*\))?)'  # Target node
    )

    match = edge_pattern.search(line)
    if match:
        source_text = match.group(1)
        edge_label = match.group(3)
        target_text = match.group(4)

        # Parse source node
        source_node = _extract_node_from_text(source_text)
        if source_node:
            nodes.append(source_node)

        # Parse target node
        target_node = _extract_node_from_text(target_text)
        if target_node:
            nodes.append(target_node)

        # Create edge if both nodes found
        if source_node and target_node:
            edge = {
                "from": source_node["id"],
                "to": target_node["id"],
                "label": edge_label.strip() if edge_label else None
            }

    return nodes, edge


def _extract_node_from_text(text: str) -> Optional[Dict[str, str]]:
    """
    Extract node info from text that may include shape definition.

    Args:
        text: Node text like "A" or "A[Label]" or "B{Decision}"

    Returns:
        Dict with id, label, type

    Example:
        >>> _extract_node_from_text("A[Start]")
        {'id': 'A', 'label': 'Start', 'type': 'action'}
        >>> _extract_node_from_text("A")
        {'id': 'A', 'label': 'A', 'type': 'action'}
    """
    text = text.strip()

    # Try to parse as full node definition
    node = _parse_node_definition(text)
    if node:
        return node

    # Extract just the ID if it has a shape we couldn't parse
    id_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)', text)
    if id_match:
        node_id = id_match.group(1)
        return {
            "id": node_id,
            "label": node_id,
            "type": "action"
        }

    return None


def _find_root_node(nodes: Dict[str, Dict], edges: List[Dict]) -> Optional[str]:
    """
    Find the root node (node with no incoming edges).

    Args:
        nodes: Dict of all nodes
        edges: List of all edges

    Returns:
        ID of root node, or first node if no clear root

    Example:
        >>> nodes = {"A": {...}, "B": {...}}
        >>> edges = [{"from": "A", "to": "B", "label": None}]
        >>> _find_root_node(nodes, edges)
        'A'
    """
    if not nodes:
        return None

    # Get all nodes that are targets of edges
    targets = {edge["to"] for edge in edges}

    # Find nodes with no incoming edges
    roots = [node_id for node_id in nodes if node_id not in targets]

    if roots:
        return roots[0]  # Return first root found

    # If no clear root (cyclic graph), return first node
    return list(nodes.keys())[0]


def get_node_children(parsed: Dict[str, Any], node_id: str) -> List[Dict[str, Any]]:
    """
    Get all child nodes of a given node with their edge labels.

    Useful for building Telegram inline keyboards from decision nodes.

    Args:
        parsed: Parsed flowchart from parse_mermaid_flowchart()
        node_id: ID of parent node

    Returns:
        List of dicts with child node info and button label

    Example:
        >>> parsed = parse_mermaid_flowchart('''
        ... flowchart TD
        ...     A{Check power?}
        ...     A -->|On| B[Continue]
        ...     A -->|Off| C[Turn on]
        ... ''')
        >>> children = get_node_children(parsed, "A")
        >>> len(children)
        2
        >>> children[0]["button_label"]
        'On'
    """
    children = []

    for edge in parsed["edges"]:
        if edge["from"] == node_id:
            child_id = edge["to"]
            child_node = parsed["nodes"].get(child_id, {})

            children.append({
                "id": child_id,
                "label": child_node.get("label", child_id),
                "type": child_node.get("type", "action"),
                "button_label": edge["label"] or child_node.get("label", child_id)
            })

    return children


def get_node_by_id(parsed: Dict[str, Any], node_id: str) -> Optional[Dict[str, str]]:
    """
    Get a specific node by its ID.

    Args:
        parsed: Parsed flowchart from parse_mermaid_flowchart()
        node_id: ID of node to retrieve

    Returns:
        Node dict with id, label, type or None if not found

    Example:
        >>> parsed = parse_mermaid_flowchart("flowchart TD\\n    A[Start] --> B[End]")
        >>> get_node_by_id(parsed, "A")
        {'id': 'A', 'label': 'Start', 'type': 'action'}
    """
    return parsed["nodes"].get(node_id)


def validate_flowchart(parsed: Dict[str, Any]) -> List[str]:
    """
    Validate a parsed flowchart for common issues.

    Checks:
        - Has at least one node
        - Has a root node
        - All edges reference valid nodes
        - Decision nodes have at least 2 outgoing edges

    Args:
        parsed: Parsed flowchart from parse_mermaid_flowchart()

    Returns:
        List of warning/error messages (empty if valid)

    Example:
        >>> parsed = {"nodes": {}, "edges": [], "root": None, "orientation": "TD"}
        >>> validate_flowchart(parsed)
        ['Flowchart has no nodes', 'No root node found']
    """
    issues = []

    if not parsed["nodes"]:
        issues.append("Flowchart has no nodes")

    if not parsed["root"]:
        issues.append("No root node found")

    # Check edges reference valid nodes
    for edge in parsed["edges"]:
        if edge["from"] not in parsed["nodes"]:
            issues.append(f"Edge references unknown source node: {edge['from']}")
        if edge["to"] not in parsed["nodes"]:
            issues.append(f"Edge references unknown target node: {edge['to']}")

    # Check decision nodes have multiple paths
    for node_id, node in parsed["nodes"].items():
        if node["type"] == "decision":
            outgoing = [e for e in parsed["edges"] if e["from"] == node_id]
            if len(outgoing) < 2:
                issues.append(f"Decision node '{node_id}' has only {len(outgoing)} outgoing edge(s)")

    return issues
