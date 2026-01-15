"""
Unit tests for the Mermaid Flowchart Parser.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rivet_pro.troubleshooting.mermaid_parser import MermaidParser, parse_mermaid


class TestMermaidParser(unittest.TestCase):
    """Test suite for MermaidParser class."""

    def test_basic_flowchart_parsing(self):
        """Test parsing a simple linear flowchart."""
        mermaid_text = """
        flowchart TD
            A[Start] --> B[End]
        """
        result = parse_mermaid(mermaid_text)

        self.assertEqual(len(result['nodes']), 2)
        self.assertEqual(len(result['edges']), 1)
        self.assertEqual(result['root'], 'A')
        self.assertEqual(result['orientation'], 'TD')

        self.assertEqual(result['nodes']['A']['label'], 'Start')
        self.assertEqual(result['nodes']['A']['type'], 'action')
        self.assertEqual(result['nodes']['B']['label'], 'End')
        self.assertEqual(result['nodes']['B']['type'], 'action')

    def test_decision_nodes(self):
        """Test parsing decision nodes (rhombus)."""
        mermaid_text = """
        flowchart TD
            A[Start] --> B{Is motor running?}
            B --> C[Check temperature]
        """
        result = parse_mermaid(mermaid_text)

        self.assertEqual(result['nodes']['B']['type'], 'decision')
        self.assertEqual(result['nodes']['B']['label'], 'Is motor running?')

    def test_edge_labels(self):
        """Test parsing edge labels for button text."""
        mermaid_text = """
        flowchart TD
            A[Start] --> B{Check?}
            B -->|Yes| C[Action 1]
            B -->|No| D[Action 2]
        """
        result = parse_mermaid(mermaid_text)

        self.assertEqual(len(result['edges']), 3)

        yes_edge = [e for e in result['edges'] if e['from'] == 'B' and e['to'] == 'C'][0]
        no_edge = [e for e in result['edges'] if e['from'] == 'B' and e['to'] == 'D'][0]

        self.assertEqual(yes_edge['label'], 'Yes')
        self.assertEqual(no_edge['label'], 'No')

    def test_left_right_orientation(self):
        """Test parsing LR (left-right) orientation."""
        mermaid_text = """
        flowchart LR
            A[Start] --> B[End]
        """
        result = parse_mermaid(mermaid_text)

        self.assertEqual(result['orientation'], 'LR')

    def test_root_node_detection(self):
        """Test that root node (no incoming edges) is correctly identified."""
        mermaid_text = """
        flowchart TD
            A[Start] --> B[Middle]
            B --> C[End]
        """
        result = parse_mermaid(mermaid_text)

        self.assertEqual(result['root'], 'A')

    def test_complex_branching(self):
        """Test parsing a complex troubleshooting flowchart with multiple branches."""
        mermaid_text = """
        flowchart TD
            A[Start] --> B{Is motor running?}
            B -->|Yes| C[Check temperature]
            B -->|No| D[Check power supply]
            C --> E{Temp > 80C?}
            E -->|Yes| F[STOP - Overheating]
            E -->|No| G[Motor OK]
            D --> H{Power present?}
            H -->|Yes| I[Check circuit breaker]
            H -->|No| J[Call electrician]
        """
        result = parse_mermaid(mermaid_text)

        self.assertEqual(len(result['nodes']), 10)
        self.assertEqual(result['root'], 'A')
        self.assertEqual(result['nodes']['B']['type'], 'decision')
        self.assertEqual(result['nodes']['E']['type'], 'decision')
        self.assertEqual(result['nodes']['H']['type'], 'decision')
        self.assertEqual(result['nodes']['A']['type'], 'action')
        self.assertEqual(result['nodes']['F']['type'], 'action')

        edges_from_b = [e for e in result['edges'] if e['from'] == 'B']
        self.assertEqual(len(edges_from_b), 2)

        labels = {e['label'] for e in edges_from_b}
        self.assertEqual(labels, {'Yes', 'No'})

    def test_motor_troubleshooting_example(self):
        """Test the exact example from the requirements."""
        mermaid_text = """
        flowchart TD
            A[Start] --> B{Is motor running?}
            B -->|Yes| C[Check temperature]
            B -->|No| D[Check power supply]
            C --> E{Temp > 80C?}
            E -->|Yes| F[WARNING STOP - Overheating]
            E -->|No| G[Motor OK]
        """
        result = parse_mermaid(mermaid_text)

        expected_nodes = {'A', 'B', 'C', 'D', 'E', 'F', 'G'}
        self.assertEqual(set(result['nodes'].keys()), expected_nodes)
        self.assertEqual(result['root'], 'A')
        self.assertEqual(result['nodes']['A']['type'], 'action')
        self.assertEqual(result['nodes']['B']['type'], 'decision')
        self.assertEqual(result['nodes']['E']['type'], 'decision')
        self.assertEqual(result['nodes']['A']['label'], 'Start')
        self.assertEqual(result['nodes']['B']['label'], 'Is motor running?')
        self.assertIn('Overheating', result['nodes']['F']['label'])


if __name__ == '__main__':
    unittest.main()
