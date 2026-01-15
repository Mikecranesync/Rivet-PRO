"""
Mermaid Flowchart Parser for RIVET Pro Troubleshooting System.

Parses Mermaid flowchart syntax into a navigable tree structure of nodes and edges.
Supports TD (top-down) and LR (left-right) orientations, decision nodes (rhombus),
and action nodes (rectangle).
"""

import re
from typing import Dict, List, Optional, Any


class MermaidParser:
    """Parser for Mermaid flowchart syntax."""

    FLOWCHART_PATTERN = re.compile(r'flowchart\s+(TD|LR)', re.IGNORECASE)
    NODE_RECTANGLE = re.compile(r'([A-Za-z0-9_]+)\[([^\]]+)\]')
    NODE_RHOMBUS = re.compile(r'([A-Za-z0-9_]+)\{([^\}]+)\}')
    NODE_CIRCLE = re.compile(r'([A-Za-z0-9_]+)\(\(([^\)]+)\)\)')
    
    EDGE_PATTERN = re.compile(
        r'([A-Za-z0-9_]+)\s*'
        r'(-\{1,2\}(?:\.|\=)\{0,2\}>)'
        r'(?:\|([^\|]+)\|)?'
        r'\s*([A-Za-z0-9_]+)'
        r'(?:\[([^\]]+)\]|\{([^\}]+)\}|\(\(([^\)]+)\)\))?'
    )

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Optional[str]]] = []
        self.orientation: Optional[str] = None
        self.root: Optional[str] = None

    def parse(self, mermaid_text: str) -> Dict[str, Any]:
        self._reset()
        mermaid_text = self._clean_text(mermaid_text)
        self._parse_flowchart_declaration(mermaid_text)
        
        lines = mermaid_text.strip().split('
')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('flowchart'):
                continue
            if self._parse_edge(line):
                continue
            self._parse_node(line)
        
        self._determine_root()
        
        return {
            'nodes': self.nodes,
            'edges': self.edges,
            'root': self.root,
            'orientation': self.orientation
        }

    def _reset(self):
        self.nodes = {}
        self.edges = []
        self.orientation = None
        self.root = None

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s*$', '', text)
        return text.strip()

    def _parse_flowchart_declaration(self, text: str):
        match = self.FLOWCHART_PATTERN.search(text)
        if match:
            self.orientation = match.group(1).upper()
        else:
            self.orientation = 'TD'

    def _parse_node(self, line: str) -> bool:
        match = self.NODE_RECTANGLE.search(line)
        if match:
            node_id, label = match.groups()
            self._add_node(node_id, label, 'action')
            return True
        
        match = self.NODE_RHOMBUS.search(line)
        if match:
            node_id, label = match.groups()
            self._add_node(node_id, label, 'decision')
            return True
        
        match = self.NODE_CIRCLE.search(line)
        if match:
            node_id, label = match.groups()
            self._add_node(node_id, label, 'terminal')
            return True
        
        return False

    def _parse_edge(self, line: str) -> bool:
        match = self.EDGE_PATTERN.search(line)
        if not match:
            return False
        
        from_node = match.group(1)
        edge_label = match.group(3)
        to_node = match.group(4)
        to_node_rect = match.group(5)
        to_node_rhomb = match.group(6)
        to_node_circle = match.group(7)
        
        if from_node not in self.nodes:
            self._add_node(from_node, from_node, 'action')
        
        if to_node_rect:
            self._add_node(to_node, to_node_rect, 'action')
        elif to_node_rhomb:
            self._add_node(to_node, to_node_rhomb, 'decision')
        elif to_node_circle:
            self._add_node(to_node, to_node_circle, 'terminal')
        elif to_node not in self.nodes:
            self._add_node(to_node, to_node, 'action')
        
        self.edges.append({
            'from': from_node,
            'to': to_node,
            'label': edge_label.strip() if edge_label else None
        })
        
        return True

    def _add_node(self, node_id: str, label: str, node_type: str):
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                'label': label.strip(),
                'type': node_type
            }

    def _determine_root(self):
        if not self.nodes:
            return
        
        nodes_with_incoming = {edge['to'] for edge in self.edges}
        potential_roots = [
            node_id for node_id in self.nodes.keys()
            if node_id not in nodes_with_incoming
        ]
        
        if potential_roots:
            self.root = potential_roots[0]
        else:
            self.root = list(self.nodes.keys())[0] if self.nodes else None


def parse_mermaid(mermaid_text: str) -> Dict[str, Any]:
    parser = MermaidParser()
    return parser.parse(mermaid_text)


__all__ = ['MermaidParser', 'parse_mermaid']
