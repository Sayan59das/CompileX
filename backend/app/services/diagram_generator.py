"""
Diagram Generator Service
Generates visual diagrams for tree and graph questions using Matplotlib and NetworkX.
"""

import base64
import io
import re
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import networkx as nx
from typing import Optional, List, Tuple


class DiagramGenerator:
    """Generates diagrams for coding questions using Matplotlib and NetworkX."""
    
    def __init__(self):
        """Initialize the diagram generator."""
        plt.style.use('dark_background')
    
    # Topics that should NEVER get a diagram, regardless of description keywords
    _NO_DIAGRAM_TOPICS = {
        'strings', 'string', 'arrays', 'array', 'dynamic programming', 'dp',
        'sorting', 'sort', 'searching', 'search', 'hashing', 'hash',
        'math', 'mathematics', 'number theory', 'bit manipulation', 'greedy',
        'backtracking', 'recursion', 'stacks', 'stack', 'queues', 'queue',
        'linked lists', 'linked list', 'two pointers', 'sliding window',
        'prefix sum', 'binary search',
    }

    # Topics that should always get a diagram
    _DIAGRAM_TOPICS = {
        'trees', 'tree', 'graph', 'graphs', 'binary-tree', 'bst',
        'binary tree', 'binary search tree',
    }

    def should_generate_diagram(self, question_text: str, tags: list) -> bool:
        """Determine if a question needs a diagram.
        
        Rules (in priority order):
        1. If the topic is explicitly a non-diagram topic → NO diagram
        2. If the topic is explicitly a diagram topic → YES diagram
        3. Only then fall back to keyword scanning of the description
        """
        tags_lower = [t.lower().strip() for t in tags]

        # Rule 1: explicit no-diagram topic wins — never show a diagram for these
        if any(t in self._NO_DIAGRAM_TOPICS for t in tags_lower):
            return False

        # Rule 2: explicit diagram topic
        if any(t in self._DIAGRAM_TOPICS for t in tags_lower):
            return True

        # Rule 3: keyword scan only when topic is unknown/generic
        # Use strict multi-word phrases to avoid false positives
        keywords = [
            'binary tree', 'binary search tree', 'bst',
            'tree structure', 'tree node', 'tree traversal',
            'graph structure', 'directed graph', 'undirected graph',
            'adjacency list', 'adjacency matrix',
        ]
        question_lower = question_text.lower()
        return any(keyword in question_lower for keyword in keywords)
    
    def generate_diagram(self, question_title: str, question_description: str, sample_input: str = None) -> str:
        """Generate a diagram for a tree/graph question."""
        try:
            print(f"[Diagram] Generating for: {question_title}")
            print(f"[Diagram] Description preview: {question_description[:200]}...")
            print(f"[Diagram] Sample input: {sample_input}")
            
            # Determine question type
            question_type = self._analyze_question_type(question_title, question_description, sample_input)
            print(f"[Diagram] Detected type: {question_type}")
            
            if question_type == 'BST':
                return self._generate_bst_diagram(sample_input)
            elif question_type == 'BINARY_TREE':
                return self._generate_binary_tree_diagram(sample_input)
            elif question_type == 'DIRECTED_GRAPH':
                return self._generate_directed_graph_diagram(sample_input)
            elif question_type == 'UNDIRECTED_GRAPH':
                return self._generate_undirected_graph_diagram(sample_input)
            else:
                return self._generate_binary_tree_diagram(sample_input)
                
        except Exception as e:
            print(f"Error generating diagram: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _analyze_question_type(self, title: str, description: str, sample_input: str) -> str:
        """Analyze question to determine structure type."""
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""

        print(f"[Diagram] Analyzing question type...")
        print(f"[Diagram] Title: {title_lower}")

        # ── Graph keywords (check first — graphs can mention "tree" in desc) ──
        graph_keywords = [
            'graph', 'directed', 'undirected', 'dag', 'topological',
            'dependency', 'shortest path', 'dijkstra', 'cycle detection',
            'connected component', 'adjacency', 'vertices', 'bfs shortest',
            'dfs', 'bellman', 'floyd', 'kruskal', 'prim',
        ]
        is_graph = (
            any(kw in title_lower for kw in graph_keywords)
            or any(kw in desc_lower for kw in graph_keywords)
        )
        if is_graph:
            print(f"[Diagram] Graph detected")
            # Explicit undirected wins over directed default
            undirected_kw = ['undirected', 'bfs', 'connected component',
                             'number of islands', 'flood fill', 'kruskal', 'prim',
                             'minimum spanning']
            directed_kw   = ['directed', 'dag', 'topological', 'dijkstra',
                             'bellman', 'floyd']
            has_directed   = any(kw in title_lower or kw in desc_lower for kw in directed_kw)
            has_undirected = any(kw in title_lower or kw in desc_lower for kw in undirected_kw)
            if has_directed and not has_undirected:
                return 'DIRECTED_GRAPH'
            return 'UNDIRECTED_GRAPH'

        # ── Distinguish level-order binary tree vs BST insertion ──────────────
        # Level-order: input format says "level-order" or "level order"
        # BST: description says "insert", "insertion order", "bst built by inserting"
        level_order_kw = [
            'level-order', 'level order', 'level order representation',
            'level-order representation', 'bfs order', 'breadth-first order',
        ]
        bst_insert_kw = [
            'insert', 'insertion order', 'bst built', 'build a bst',
            'construct a bst', 'inserting values',
        ]

        desc_and_title = title_lower + ' ' + desc_lower
        is_level_order = any(kw in desc_and_title for kw in level_order_kw)
        is_bst_insert  = any(kw in desc_and_title for kw in bst_insert_kw)

        # Also detect level-order from the sample input shape:
        # If first line is a single integer N and second line has N space-separated
        # values, it's almost certainly level-order representation.
        if sample_input and not is_bst_insert:
            lines = [l.strip() for l in sample_input.strip().split('\n') if l.strip()]
            if len(lines) >= 2:
                first_nums = re.findall(r'-?\d+', lines[0])
                second_nums = re.findall(r'-?\d+', lines[1])
                if len(first_nums) == 1 and len(second_nums) > 1:
                    # N on first line, values on second → level-order
                    is_level_order = True

        tree_keywords = [
            'binary tree', 'binary search tree', 'bst', 'tree',
            'inorder', 'preorder', 'postorder', 'level order',
            'diameter', 'depth', 'height', 'ancestor', 'traversal',
            'root', 'leaf', 'subtree',
        ]
        is_tree = (
            any(kw in title_lower for kw in tree_keywords)
            or any(kw in desc_lower for kw in tree_keywords)
        )

        if is_tree:
            if is_bst_insert and not is_level_order:
                print(f"[Diagram] BST (insertion order) detected")
                return 'BST'
            else:
                # Default for tree questions: level-order array representation
                print(f"[Diagram] Binary tree (level-order) detected")
                return 'BINARY_TREE'

        print(f"[Diagram] Defaulting to binary tree (level-order)")
        return 'BINARY_TREE'
    
    def _generate_bst_diagram(self, sample_input: Optional[str]) -> str:
        """Generate BST diagram from insertion order."""
        try:
            values = self._parse_tree_input(sample_input)
            if not values:
                values = [50, 30, 70, 20, 40, 60, 80]
            
            print(f"[BST] Building from: {values}")
            
            fig, ax = plt.subplots(figsize=(14, 10), facecolor='#0a0a0a')
            ax.set_facecolor('#0a0a0a')
            ax.axis('off')
            
            # Build BST
            G = nx.DiGraph()
            root, node_map = self._build_bst(values)
            self._add_bst_edges(G, root, node_map)
            positions = self._calculate_bst_positions(root, node_map)
            
            # Draw
            self._draw_tree(G, positions, ax, "BST Structure")
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            print(f"Error in BST diagram: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_binary_tree_diagram(self, sample_input: Optional[str]) -> str:
        """
        Generate a binary tree diagram from level-order input.
        Input format: N on first line, then N space-separated values on second line.
        -1 (or null) means the node is absent.
        Uses array-index parent-child: left child of i = 2i+1, right child = 2i+2.
        """
        try:
            values = self._parse_tree_input(sample_input)
            if not values:
                values = [1, 2, 3, 4, 5, 6, 7]

            print(f"[BinaryTree] Building level-order tree from: {values}")

            # Filter out null markers (-1) but keep track of positions
            # Build the tree using array indexing (level-order)
            G = nx.DiGraph()

            # Add all non-null nodes
            for i, val in enumerate(values):
                if val != -1:
                    G.add_node(i, label=str(val))

            # Add edges: parent i → left child 2i+1, right child 2i+2
            for i in range(len(values)):
                if values[i] == -1:
                    continue
                left = 2 * i + 1
                right = 2 * i + 2
                if left < len(values) and values[left] != -1:
                    G.add_edge(i, left)
                if right < len(values) and values[right] != -1:
                    G.add_edge(i, right)

            if len(G.nodes) == 0:
                return None

            fig, ax = plt.subplots(figsize=(14, 10), facecolor='#0a0a0a')
            ax.set_facecolor('#0a0a0a')
            ax.axis('off')

            # Use hierarchical layout rooted at node 0
            positions = self._hierarchy_pos(G, 0, width=12, vert_gap=2)
            self._draw_tree(G, positions, ax, "Binary Tree Structure")

            return self._fig_to_base64(fig)

        except Exception as e:
            print(f"Error in binary tree diagram: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_directed_graph_diagram(self, sample_input: Optional[str]) -> str:
        """Generate directed graph diagram."""
        try:
            edges = self._parse_graph_input(sample_input)
            if not edges:
                edges = [(0, 1), (0, 2), (1, 3), (2, 3)]
            
            print(f"[Graph] Building directed graph from: {edges}")
            
            fig, ax = plt.subplots(figsize=(14, 10), facecolor='#0a0a0a')
            ax.set_facecolor('#0a0a0a')
            ax.axis('off')
            
            G = nx.DiGraph()
            G.add_edges_from(edges)
            
            if nx.is_directed_acyclic_graph(G):
                positions = self._topological_layout(G)
            else:
                positions = nx.spring_layout(G, k=3, iterations=50, seed=42)
            
            self._draw_graph(G, positions, ax, "Directed Graph", directed=True)
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            print(f"Error in directed graph diagram: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_undirected_graph_diagram(self, sample_input: Optional[str]) -> str:
        """Generate undirected graph diagram."""
        try:
            edges = self._parse_graph_input(sample_input)
            if not edges:
                edges = [(0, 1), (0, 2), (1, 3), (2, 3)]
            
            print(f"[Graph] Building undirected graph from: {edges}")
            
            fig, ax = plt.subplots(figsize=(14, 10), facecolor='#0a0a0a')
            ax.set_facecolor('#0a0a0a')
            ax.axis('off')
            
            G = nx.Graph()  # Undirected graph
            G.add_edges_from(edges)
            
            # Use spring layout for undirected graphs
            positions = nx.spring_layout(G, k=3, iterations=50, seed=42)
            
            self._draw_graph(G, positions, ax, "Undirected Graph", directed=False)
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            print(f"Error in undirected graph diagram: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_bst(self, values):
        """Build BST structure by inserting values in order."""
        class BSTNode:
            def __init__(self, val, idx):
                self.val = val
                self.idx = idx
                self.left = None
                self.right = None
        
        if not values:
            return None, {}
        
        # Create root node
        root = BSTNode(values[0], 0)
        node_map = {0: root}
        
        # Insert remaining values following BST rules
        for i, val in enumerate(values[1:], 1):
            new_node = BSTNode(val, i)
            node_map[i] = new_node
            
            # Find correct position and insert
            current = root
            while True:
                if val < current.val:
                    if current.left is None:
                        current.left = new_node
                        break
                    current = current.left
                else:
                    if current.right is None:
                        current.right = new_node
                        break
                    current = current.right
        
        return root, node_map
    
    def _add_bst_edges(self, G, root, node_map):
        """Add edges from BST structure."""
        def traverse(node):
            if node:
                G.add_node(node.idx, label=str(node.val))
                if node.left:
                    G.add_edge(node.idx, node.left.idx)
                    traverse(node.left)
                if node.right:
                    G.add_edge(node.idx, node.right.idx)
                    traverse(node.right)
        
        traverse(root)
    
    def _calculate_bst_positions(self, root, node_map):
        """
        Calculate BST node positions using in-order traversal for x-axis
        so nodes are evenly spaced and never overlap.
        """
        positions = {}
        counter = [0]

        def _inorder(node):
            if node is None:
                return
            _inorder(node.left)
            positions[node.idx] = (counter[0] * 2.0, -node_depth(node, root) * 2.0)
            counter[0] += 1
            _inorder(node.right)

        def node_depth(node, root):
            """Find depth of node by traversing from root."""
            depth = 0
            cur = root
            while cur and cur.idx != node.idx:
                depth += 1
                if node.val < cur.val:
                    cur = cur.left
                else:
                    cur = cur.right
            return depth

        _inorder(root)

        # Centre around x=0
        if positions:
            xs = [p[0] for p in positions.values()]
            mid = (max(xs) + min(xs)) / 2
            positions = {n: (x - mid, y) for n, (x, y) in positions.items()}

        return positions
    
    def _topological_layout(self, G):
        """Create topological layout for DAG."""
        try:
            layers = list(nx.topological_generations(G))
            positions = {}
            for layer_idx, layer in enumerate(layers):
                layer_nodes = list(layer)
                for node_idx, node in enumerate(layer_nodes):
                    x = (node_idx - len(layer_nodes) / 2) * 3
                    y = -layer_idx * 3
                    positions[node] = (x, y)
            return positions
        except:
            return nx.spring_layout(G, k=3, iterations=50, seed=42)
    
    def _hierarchy_pos(self, G, root, width=12., vert_gap=2.0, xcenter=0.):
        """
        Create a proper hierarchical (top-down) layout for a binary tree.
        Assigns x positions by in-order traversal so nodes never overlap.
        """
        pos = {}
        # Assign x by in-order rank (left-to-right ordering)
        counter = [0]

        def _inorder(node, depth):
            if node not in G.nodes:
                return
            children = list(G.successors(node))
            left  = children[0] if len(children) > 0 else None
            right = children[1] if len(children) > 1 else None

            if left is not None:
                _inorder(left, depth + 1)

            pos[node] = (counter[0] * 2.0, -depth * vert_gap)
            counter[0] += 1

            if right is not None:
                _inorder(right, depth + 1)

        _inorder(root, 0)

        # Centre the layout around x=0
        if pos:
            xs = [p[0] for p in pos.values()]
            mid = (max(xs) + min(xs)) / 2
            pos = {n: (x - mid, y) for n, (x, y) in pos.items()}

        return pos
    
    def _draw_tree(self, G, positions, ax, title):
        """Draw tree with styling."""
        nx.draw_networkx_edges(
            G, positions, ax=ax,
            edge_color='#6366f1',
            width=3,
            alpha=0.7,
            arrows=True,
            arrowsize=20,
            arrowstyle='->',
            node_size=2500
        )
        
        node_colors = ['#8b5cf6' if i == 0 else '#a78bfa' for i in G.nodes()]
        nx.draw_networkx_nodes(
            G, positions, ax=ax,
            node_color=node_colors,
            node_size=2500,
            edgecolors='#c4b5fd',
            linewidths=3
        )
        
        labels = nx.get_node_attributes(G, 'label')
        nx.draw_networkx_labels(
            G, positions, labels, ax=ax,
            font_size=16,
            font_weight='bold',
            font_color='white'
        )
        
        plt.title(title, fontsize=18, fontweight='bold', color='#a78bfa', pad=25)
    
    def _draw_graph(self, G, positions, ax, title, directed=True):
        """Draw graph with styling."""
        # Draw edges
        if directed:
            nx.draw_networkx_edges(
                G, positions, ax=ax,
                edge_color='#6366f1',
                width=3,
                alpha=0.7,
                arrows=True,
                arrowsize=25,
                arrowstyle='->',
                connectionstyle='arc3,rad=0.1',
                node_size=2500
            )
        else:
            # Undirected graph - no arrows
            nx.draw_networkx_edges(
                G, positions, ax=ax,
                edge_color='#6366f1',
                width=3,
                alpha=0.7,
                node_size=2500
            )
        
        nx.draw_networkx_nodes(
            G, positions, ax=ax,
            node_color='#8b5cf6',
            node_size=2500,
            edgecolors='#c4b5fd',
            linewidths=3
        )
        
        nx.draw_networkx_labels(
            G, positions, ax=ax,
            font_size=16,
            font_weight='bold',
            font_color='white'
        )
        
        plt.title(title, fontsize=18, fontweight='bold', color='#a78bfa', pad=25)
    
    def _fig_to_base64(self, fig):
        """Convert figure to base64."""
        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format='png', dpi=150, facecolor='#0a0a0a', edgecolor='none', bbox_inches='tight')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        return f"data:image/png;base64,{img_str}"
    
    def _parse_tree_input(self, sample_input: Optional[str]) -> List[int]:
        """Parse tree input - handle different input formats."""
        if not sample_input:
            return []
        
        try:
            lines = sample_input.strip().split('\n')
            if not lines:
                return []
            
            # Check if first line is just a count (N)
            first_line_nums = re.findall(r'-?\d+', lines[0])
            
            # If first line has only 1 number and there's a second line, use second line
            if len(first_line_nums) == 1 and len(lines) > 1:
                # First line is N (count), second line has the actual values
                second_line = lines[1]
                numbers = re.findall(r'-?\d+', second_line)
                values = [int(n) for n in numbers[:20]]
                print(f"[Parse] Tree input (using line 2): {second_line}")
                print(f"[Parse] Parsed values: {values}")
                return values
            
            # Otherwise, use first line
            numbers = re.findall(r'-?\d+', lines[0])
            values = [int(n) for n in numbers[:20]]
            
            print(f"[Parse] Tree input (using line 1): {lines[0]}")
            print(f"[Parse] Parsed values: {values}")
            
            return values
        except Exception as e:
            print(f"[Parse] Error parsing tree input: {e}")
            return []
    
    def _parse_graph_input(self, sample_input: Optional[str]) -> List[Tuple[int, int]]:
        """Parse graph edges."""
        if not sample_input:
            return []
        
        try:
            lines = sample_input.strip().split('\n')
            if len(lines) == 0:
                return []
            
            edges = []
            start_idx = 0
            
            # Check if first line is "N M" or "N M S D" format (metadata)
            first_line_nums = re.findall(r'-?\d+', lines[0])
            if len(first_line_nums) >= 2 and len(lines) > 1:
                # First line is metadata (N M or N M S D), skip it
                start_idx = 1
                print(f"[Parse] Graph metadata: {lines[0]}")
            
            # Parse edges from remaining lines
            for line in lines[start_idx:]:
                numbers = re.findall(r'-?\d+', line)
                if len(numbers) >= 2:
                    # Take first two numbers as edge (u, v)
                    edges.append((int(numbers[0]), int(numbers[1])))
            
            print(f"[Parse] Graph edges: {edges[:10]}...")  # Show first 10
            return edges[:30]  # Limit to 30 edges for visualization
        except Exception as e:
            print(f"[Parse] Error parsing graph: {e}")
            return []


# Global instance
diagram_generator = DiagramGenerator()
