"""
Unit tests for Mermaid Diagram Parser.

Tests cover:
- Basic flowchart parsing
- TD and LR orientations
- Decision and action nodes
- Edge labels for button text
- Branching flowcharts
- Validation
"""

import pytest
from rivet_pro.core.utils.mermaid_parser import (
    parse_mermaid_flowchart,
    get_node_children,
    get_node_by_id,
    validate_flowchart,
    _parse_orientation,
    _parse_node_definition,
    _parse_edge_line,
)


class TestBasicParsing:
    """Test basic flowchart parsing functionality."""

    def test_simple_two_node_flowchart(self):
        """Parse simple A --> B flowchart."""
        mermaid = """
        flowchart TD
            A[Start] --> B[End]
        """
        result = parse_mermaid_flowchart(mermaid)

        assert result["orientation"] == "TD"
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["root"] == "A"

    def test_nodes_have_correct_properties(self):
        """Verify node structure has id, label, type."""
        mermaid = """
        flowchart TD
            A[Start Here]
        """
        result = parse_mermaid_flowchart(mermaid)

        node_a = result["nodes"]["A"]
        assert node_a["id"] == "A"
        assert node_a["label"] == "Start Here"
        assert node_a["type"] == "action"

    def test_edge_structure(self):
        """Verify edge structure has from, to, label."""
        mermaid = """
        flowchart TD
            A --> B
        """
        result = parse_mermaid_flowchart(mermaid)

        edge = result["edges"][0]
        assert edge["from"] == "A"
        assert edge["to"] == "B"
        assert edge["label"] is None


class TestOrientations:
    """Test TD and LR orientation support."""

    def test_top_down_orientation(self):
        """Parse flowchart TD orientation."""
        mermaid = "flowchart TD\n    A --> B"
        result = parse_mermaid_flowchart(mermaid)
        assert result["orientation"] == "TD"

    def test_left_right_orientation(self):
        """Parse flowchart LR orientation."""
        mermaid = "flowchart LR\n    A --> B"
        result = parse_mermaid_flowchart(mermaid)
        assert result["orientation"] == "LR"

    def test_top_bottom_orientation(self):
        """Parse flowchart TB orientation (same as TD)."""
        mermaid = "flowchart TB\n    A --> B"
        result = parse_mermaid_flowchart(mermaid)
        assert result["orientation"] == "TB"

    def test_right_left_orientation(self):
        """Parse flowchart RL orientation."""
        mermaid = "flowchart RL\n    A --> B"
        result = parse_mermaid_flowchart(mermaid)
        assert result["orientation"] == "RL"

    def test_default_orientation(self):
        """Default to TD when no orientation specified."""
        lines = ["A --> B"]
        assert _parse_orientation(lines) == "TD"

    def test_graph_keyword_also_works(self):
        """Support 'graph' keyword in addition to 'flowchart'."""
        mermaid = "graph LR\n    A --> B"
        result = parse_mermaid_flowchart(mermaid)
        assert result["orientation"] == "LR"


class TestNodeTypes:
    """Test decision and action node parsing."""

    def test_action_node_square_brackets(self):
        """Parse action node with [square brackets]."""
        node = _parse_node_definition("A[Action Step]")
        assert node["id"] == "A"
        assert node["label"] == "Action Step"
        assert node["type"] == "action"

    def test_decision_node_curly_braces(self):
        """Parse decision node with {curly braces}."""
        node = _parse_node_definition("B{Is it working?}")
        assert node["id"] == "B"
        assert node["label"] == "Is it working?"
        assert node["type"] == "decision"

    def test_rounded_node_parentheses(self):
        """Parse rounded node with (parentheses)."""
        node = _parse_node_definition("C(Rounded Step)")
        assert node["id"] == "C"
        assert node["label"] == "Rounded Step"
        assert node["type"] == "action"

    def test_plain_node_id_only(self):
        """Parse node with just ID (no shape)."""
        node = _parse_node_definition("NodeID")
        assert node["id"] == "NodeID"
        assert node["label"] == "NodeID"
        assert node["type"] == "action"

    def test_decision_nodes_in_full_flowchart(self):
        """Decision nodes identified correctly in full parse."""
        mermaid = """
        flowchart TD
            A[Start] --> B{Is power on?}
            B -->|Yes| C[Continue]
            B -->|No| D[Turn on power]
        """
        result = parse_mermaid_flowchart(mermaid)

        assert result["nodes"]["A"]["type"] == "action"
        assert result["nodes"]["B"]["type"] == "decision"
        assert result["nodes"]["C"]["type"] == "action"
        assert result["nodes"]["D"]["type"] == "action"


class TestEdgeLabels:
    """Test edge label preservation for button text."""

    def test_edge_with_label(self):
        """Parse edge with |label| syntax."""
        mermaid = """
        flowchart TD
            A{Question?} -->|Yes| B[Do this]
        """
        result = parse_mermaid_flowchart(mermaid)

        edge = result["edges"][0]
        assert edge["label"] == "Yes"

    def test_edge_without_label(self):
        """Edge without label has None."""
        mermaid = """
        flowchart TD
            A --> B
        """
        result = parse_mermaid_flowchart(mermaid)

        edge = result["edges"][0]
        assert edge["label"] is None

    def test_multiple_labeled_edges(self):
        """Parse multiple edges with different labels."""
        mermaid = """
        flowchart TD
            A{Check} -->|Option 1| B
            A -->|Option 2| C
            A -->|Option 3| D
        """
        result = parse_mermaid_flowchart(mermaid)

        labels = [e["label"] for e in result["edges"]]
        assert "Option 1" in labels
        assert "Option 2" in labels
        assert "Option 3" in labels

    def test_edge_label_with_spaces(self):
        """Edge labels can contain spaces."""
        nodes, edge = _parse_edge_line("A -->|Yes, continue| B")
        assert edge["label"] == "Yes, continue"


class TestBranching:
    """Test branching flowchart structures."""

    def test_binary_decision_tree(self):
        """Parse binary yes/no decision tree."""
        mermaid = """
        flowchart TD
            A{Is power on?}
            A -->|Yes| B[Check display]
            A -->|No| C[Turn on power]
            C --> D{Power restored?}
            D -->|Yes| B
            D -->|No| E[Call support]
        """
        result = parse_mermaid_flowchart(mermaid)

        assert len(result["nodes"]) == 5
        assert len(result["edges"]) == 5
        assert result["root"] == "A"

    def test_multi_way_branch(self):
        """Parse node with 3+ outgoing edges."""
        mermaid = """
        flowchart TD
            A{Select action}
            A -->|Option 1| B
            A -->|Option 2| C
            A -->|Option 3| D
            A -->|Option 4| E
        """
        result = parse_mermaid_flowchart(mermaid)

        # A has 4 outgoing edges
        a_edges = [e for e in result["edges"] if e["from"] == "A"]
        assert len(a_edges) == 4

    def test_convergent_paths(self):
        """Parse paths that converge to same node."""
        mermaid = """
        flowchart TD
            A{Choice} -->|Left| B[Path 1]
            A -->|Right| C[Path 2]
            B --> D[End]
            C --> D
        """
        result = parse_mermaid_flowchart(mermaid)

        # D has 2 incoming edges
        d_incoming = [e for e in result["edges"] if e["to"] == "D"]
        assert len(d_incoming) == 2


class TestHelperFunctions:
    """Test helper functions for navigation."""

    def test_get_node_children(self):
        """Get all children of a node with button labels."""
        mermaid = """
        flowchart TD
            A{Check power?}
            A -->|On| B[Continue]
            A -->|Off| C[Turn on]
        """
        parsed = parse_mermaid_flowchart(mermaid)
        children = get_node_children(parsed, "A")

        assert len(children) == 2

        # Check button labels come from edge labels
        button_labels = [c["button_label"] for c in children]
        assert "On" in button_labels
        assert "Off" in button_labels

    def test_get_node_children_no_edge_label(self):
        """Children without edge labels use node label as button."""
        mermaid = """
        flowchart TD
            A --> B[Next Step]
        """
        parsed = parse_mermaid_flowchart(mermaid)
        children = get_node_children(parsed, "A")

        assert len(children) == 1
        assert children[0]["button_label"] == "Next Step"

    def test_get_node_by_id(self):
        """Retrieve specific node by ID."""
        mermaid = """
        flowchart TD
            A[Start] --> B[Middle] --> C[End]
        """
        parsed = parse_mermaid_flowchart(mermaid)

        node_b = get_node_by_id(parsed, "B")
        assert node_b["label"] == "Middle"

    def test_get_nonexistent_node(self):
        """Return None for nonexistent node ID."""
        mermaid = "flowchart TD\n    A --> B"
        parsed = parse_mermaid_flowchart(mermaid)

        result = get_node_by_id(parsed, "Z")
        assert result is None


class TestValidation:
    """Test flowchart validation."""

    def test_valid_flowchart_no_issues(self):
        """Valid flowchart returns empty issues list."""
        mermaid = """
        flowchart TD
            A{Decision} -->|Yes| B
            A -->|No| C
        """
        parsed = parse_mermaid_flowchart(mermaid)
        issues = validate_flowchart(parsed)

        assert len(issues) == 0

    def test_empty_flowchart_has_issues(self):
        """Empty flowchart flagged as invalid."""
        parsed = {
            "orientation": "TD",
            "nodes": {},
            "edges": [],
            "root": None
        }
        issues = validate_flowchart(parsed)

        assert "Flowchart has no nodes" in issues
        assert "No root node found" in issues

    def test_decision_node_single_path_warning(self):
        """Decision node with single path flagged."""
        mermaid = """
        flowchart TD
            A{Decision} -->|Only one| B
        """
        parsed = parse_mermaid_flowchart(mermaid)
        issues = validate_flowchart(parsed)

        assert any("Decision node 'A' has only 1" in issue for issue in issues)


class TestRootNodeDetection:
    """Test automatic root node detection."""

    def test_single_root_detected(self):
        """Single entry point correctly identified as root."""
        mermaid = """
        flowchart TD
            Start[Begin Here] --> A
            A --> B
            B --> End[Done]
        """
        parsed = parse_mermaid_flowchart(mermaid)
        assert parsed["root"] == "Start"

    def test_first_node_as_root(self):
        """First declared node is root when topology unclear."""
        mermaid = """
        flowchart TD
            A --> B
        """
        parsed = parse_mermaid_flowchart(mermaid)
        assert parsed["root"] == "A"


class TestEdgeCases:
    """Test edge cases and special syntax."""

    def test_comments_ignored(self):
        """Mermaid comments (%%) are ignored."""
        mermaid = """
        flowchart TD
            %% This is a comment
            A[Start] --> B[End]
            %% Another comment
        """
        result = parse_mermaid_flowchart(mermaid)
        assert len(result["nodes"]) == 2

    def test_empty_lines_handled(self):
        """Empty lines don't break parsing."""
        mermaid = """
        flowchart TD

            A --> B

            B --> C

        """
        result = parse_mermaid_flowchart(mermaid)
        assert len(result["nodes"]) == 3

    def test_node_id_with_numbers(self):
        """Node IDs can contain numbers."""
        mermaid = """
        flowchart TD
            Step1[First] --> Step2[Second]
        """
        result = parse_mermaid_flowchart(mermaid)
        assert "Step1" in result["nodes"]
        assert "Step2" in result["nodes"]

    def test_node_id_with_underscores(self):
        """Node IDs can contain underscores."""
        mermaid = """
        flowchart TD
            start_node --> end_node
        """
        result = parse_mermaid_flowchart(mermaid)
        assert "start_node" in result["nodes"]
        assert "end_node" in result["nodes"]

    def test_multiline_node_labels_not_supported(self):
        """Multiline labels treated as single line (limitation)."""
        # This is a known limitation - labels should be single line
        node = _parse_node_definition("A[Single Line Label]")
        assert node is not None


class TestRealWorldExample:
    """Test with realistic troubleshooting flowchart."""

    def test_vfd_troubleshooting_flowchart(self):
        """Parse a realistic VFD troubleshooting decision tree."""
        mermaid = """
        flowchart TD
            START[VFD Fault Alarm] --> CHECK{What fault code?}
            CHECK -->|F001 Overcurrent| OC[Check motor load]
            CHECK -->|F002 Overvoltage| OV[Check supply voltage]
            CHECK -->|F003 Undervoltage| UV[Check power supply]
            CHECK -->|Unknown| UK[Note the code]

            OC --> OC_Q{Motor overloaded?}
            OC_Q -->|Yes| OC_FIX[Reduce load or upsize VFD]
            OC_Q -->|No| OC_CABLE[Check motor cables]

            OV --> OV_Q{Voltage > 10% high?}
            OV_Q -->|Yes| OV_TAP[Adjust transformer tap]
            OV_Q -->|No| OV_REGEN[Check regeneration braking]

            UK --> CALL[Call technical support]
        """
        result = parse_mermaid_flowchart(mermaid)

        # Verify structure
        assert result["root"] == "START"
        assert len(result["nodes"]) == 14

        # Verify decision nodes detected
        assert result["nodes"]["CHECK"]["type"] == "decision"
        assert result["nodes"]["OC_Q"]["type"] == "decision"
        assert result["nodes"]["OV_Q"]["type"] == "decision"

        # Verify action nodes
        assert result["nodes"]["OC"]["type"] == "action"
        assert result["nodes"]["CALL"]["type"] == "action"

        # Verify edge labels preserved
        check_edges = [e for e in result["edges"] if e["from"] == "CHECK"]
        labels = [e["label"] for e in check_edges]
        assert "F001 Overcurrent" in labels
        assert "Unknown" in labels

        # Verify navigation works
        check_children = get_node_children(result, "CHECK")
        assert len(check_children) == 4
        button_labels = [c["button_label"] for c in check_children]
        assert "F001 Overcurrent" in button_labels
