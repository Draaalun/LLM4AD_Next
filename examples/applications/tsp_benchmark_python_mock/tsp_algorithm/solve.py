#!/usr/bin/env python3
"""Traveling Salesman Problem (TSP) solver with EVOLVE markers for LLM4AD optimization.

This is a baseline Nearest Neighbor implementation that will be evolved
by the LLM4AD system to find better TSP tours.
"""

# EVOLVE_START
import heapq
import json
import sys
from collections import deque

import numpy as np


class KMeansClusterer:
    """K-means clustering for TSP preprocessing.

    This class implements k-means clustering to identify spatial clusters
    of cities, providing centroids as strategic starting points for the tour.

    Key features:
    - Adaptive number of clusters based on problem size
    - Efficient convergence with early stopping
    - Centroid-based initialization for better quality
    """

    def __init__(self, nodes, n_clusters=None):
        """Initialize the k-means clusterer.

        Args:
            nodes: NumPy array of shape (n, 2) containing city coordinates
            n_clusters: Number of clusters (auto-determined if None)
        """
        self.nodes = nodes
        self.n = len(nodes)

        # Determine optimal number of clusters
        # Use sqrt(n) as a heuristic, bounded between 3 and 10
        if n_clusters is None:
            n_clusters = max(3, min(10, int(np.sqrt(self.n))))

        self.n_clusters = n_clusters
        self.centroids = None
        self.labels = None

    def fit(self, max_iters=100, tolerance=1e-6):
        """Run k-means clustering.

        Args:
            max_iters: Maximum number of iterations
            tolerance: Convergence tolerance for centroid movement

        Returns:
            tuple: (centroids, labels) where centroids is (k, 2) array
                   and labels is (n,) array of cluster assignments
        """
        if self.n <= self.n_clusters:
            # Fewer points than clusters, each point is its own cluster
            self.centroids = self.nodes.copy()
            self.labels = np.arange(self.n)
            return self.centroids, self.labels

        # Initialize centroids using k-means++ like approach
        self.centroids = self._initialize_centroids()

        for _iteration in range(max_iters):
            old_centroids = self.centroids.copy()

            # Assign each point to nearest centroid
            self.labels = self._assign_to_centroids()

            # Update centroids
            self.centroids = self._update_centroids()

            # Check for convergence
            movement = np.sum(np.abs(self.centroids - old_centroids))
            if movement < tolerance:
                break

        return self.centroids, self.labels

    def _initialize_centroids(self):
        """Initialize centroids using a spread-based approach.

        Returns:
            NumPy array of shape (n_clusters, 2) with initial centroids
        """
        # Start with random point
        indices = [np.random.randint(0, self.n)]
        centroids = [self.nodes[indices[0]]]

        # Select remaining centroids to maximize spread
        for _ in range(1, self.n_clusters):
            # Compute minimum distances to existing centroids
            distances = np.full(self.n, np.inf)
            for idx in indices:
                diff = self.nodes - self.nodes[idx]
                dist_sq = np.sum(diff * diff, axis=1)
                distances = np.minimum(distances, dist_sq)

            # Select point farthest from existing centroids
            new_idx = np.argmax(distances)
            indices.append(new_idx)
            centroids.append(self.nodes[new_idx])

        return np.array(centroids)

    def _assign_to_centroids(self):
        """Assign each node to its nearest centroid.

        Returns:
            NumPy array of shape (n,) with cluster labels
        """
        labels = np.zeros(self.n, dtype=int)

        for i in range(self.n):
            # Find nearest centroid
            diff = self.centroids - self.nodes[i]
            dist_sq = np.sum(diff * diff, axis=1)
            labels[i] = np.argmin(dist_sq)

        return labels

    def _update_centroids(self):
        """Update centroids as mean of assigned points.

        Returns:
            NumPy array of shape (n_clusters, 2) with updated centroids
        """
        new_centroids = np.zeros_like(self.centroids)

        for k in range(self.n_clusters):
            mask = self.labels == k
            if np.any(mask):
                new_centroids[k] = self.nodes[mask].mean(axis=0)
            else:
                # Empty cluster: reinitialize at random point
                new_centroids[k] = self.nodes[np.random.randint(0, self.n)]

        return new_centroids

    def get_cluster_nodes(self, cluster_id):
        """Get all nodes belonging to a specific cluster.

        Args:
            cluster_id: ID of the cluster

        Returns:
            NumPy array of indices of nodes in the cluster
        """
        return np.where(self.labels == cluster_id)[0]


class KDTreeNode:
    """Node class for KD-Tree spatial index.

    Each node represents a region of space and contains information
    about points within that region for efficient nearest neighbor queries.
    """

    def __init__(self, point_indices, min_bound, max_bound, depth=0):
        """Initialize a KD-Tree node.

        Args:
            point_indices: Array of point indices in this node
            min_bound: Array [min_x, min_y] of minimum coordinates
            max_bound: Array [max_x, max_y] of maximum coordinates
            depth: Depth of this node in the tree
        """
        self.point_indices = point_indices
        self.min_bound = np.array(min_bound, dtype=np.float64)
        self.max_bound = np.array(max_bound, dtype=np.float64)
        self.depth = depth
        self.split_dim = depth % 2  # Alternate between x (0) and y (1)
        self.split_val = None
        self.left = None
        self.right = None
        self.is_leaf = False

        # Compute node center for distance calculations
        self.center = (self.min_bound + self.max_bound) * 0.5


class KDTreeIndex:
    """K-Dimensional Tree (KD-Tree) for hierarchical spatial indexing.

    This class implements a KD-Tree data structure for efficient spatial queries.
    The tree recursively partitions space along alternating dimensions, enabling
    efficient nearest neighbor searches with logarithmic complexity on average.

    Key features:
    - Hierarchical spatial partitioning based on point density
    - Early pruning of distant branches during search
    - Support for lazy deletion of points
    - Two-phase search: quick local + thorough global refinement
    """

    def __init__(self, nodes, min_leaf_size=5, max_depth=20):
        """Initialize the KD-Tree spatial index.

        Args:
            nodes: NumPy array of shape (n, 2) containing city coordinates
            min_leaf_size: Minimum number of points before stopping subdivision
            max_depth: Maximum depth of the tree to prevent over-subdivision
        """
        self.nodes = nodes
        self.n = len(nodes)
        self.min_leaf_size = min_leaf_size
        self.max_depth = max_depth

        # Compute global bounds
        self.min_coords = nodes.min(axis=0)
        self.max_coords = nodes.max(axis=0)
        self.global_range = self.max_coords - self.min_coords

        # Ensure non-zero range to avoid division issues
        if self.global_range[0] == 0:
            self.global_range[0] = 1.0
        if self.global_range[1] == 0:
            self.global_range[1] = 1.0

        # Build the tree
        all_indices = np.arange(self.n)
        self.root = self._build_tree(all_indices, self.min_coords, self.max_coords, 0)

        # Active mask for lazy removal: True means point is still available
        self.active = np.ones(self.n, dtype=bool)

        # Temporal locality tracking
        self.recently_visited = deque(maxlen=5)
        self.visit_time = np.full(self.n, -1, dtype=int)

        # Precompute squared distances for fast k-NN lookup
        self._precompute_distances()

        # Track last nearest neighbor distance for adaptive search
        self.last_nearest_dist = np.inf

        # Track tour for temporal relevance
        self.tour = []

    def _build_tree(self, indices, min_bound, max_bound, depth):
        """Recursively build the KD-Tree.

        Args:
            indices: Array of point indices in this subtree
            min_bound: Minimum coordinates of this region
            max_bound: Maximum coordinates of this region
            depth: Current depth in the tree

        Returns:
            KDTreeNode: Root node of the constructed subtree
        """
        node = KDTreeNode(indices, min_bound, max_bound, depth)

        # Check if we should stop splitting
        n_points = len(indices)
        if n_points <= self.min_leaf_size or depth >= self.max_depth:
            node.is_leaf = True
            return node

        # Determine split dimension and value
        split_dim = node.split_dim
        points = self.nodes[indices]

        # Use median for balanced tree
        split_vals = points[:, split_dim]
        median_val = np.median(split_vals)
        node.split_val = median_val

        # Partition indices into left and right subtrees
        left_mask = points[:, split_dim] <= median_val
        right_mask = points[:, split_dim] > median_val

        left_indices = indices[left_mask]
        right_indices = indices[right_mask]

        # Handle edge case: all points on one side
        if len(left_indices) == n_points or len(right_indices) == n_points:
            # Split differently: use a point slightly above median
            if len(left_indices) == n_points:
                # Move one point to right
                max_idx = np.argmax(points[:, split_dim])
                max_point_idx = indices[max_idx]
                left_indices = indices[indices != max_point_idx]
                right_indices = np.array([max_point_idx])
            else:
                # Move one point to left
                min_idx = np.argmin(points[:, split_dim])
                min_point_idx = indices[min_idx]
                right_indices = indices[indices != min_point_idx]
                left_indices = np.array([min_point_idx])

        # Create new bounds for children
        new_min_bound = min_bound.copy()
        new_max_bound = max_bound.copy()

        # Left child: everything <= split_val
        left_max = new_max_bound.copy()
        left_max[split_dim] = median_val

        # Right child: everything > split_val
        right_min = new_min_bound.copy()
        right_min[split_dim] = median_val

        # Recursively build subtrees
        if len(left_indices) > 0:
            node.left = self._build_tree(left_indices, new_min_bound, left_max, depth + 1)
        if len(right_indices) > 0:
            node.right = self._build_tree(right_indices, right_min, new_max_bound, depth + 1)

        return node

    def _precompute_distances(self):
        """Precompute all pairwise squared distances for fast k-NN."""
        n = self.n
        self.dist_sq_matrix = np.zeros((n, n), dtype=np.float64)

        for i in range(n):
            diff = self.nodes[i] - self.nodes
            self.dist_sq_matrix[i] = np.sum(diff * diff, axis=1)

    def remove_node(self, node_idx, visit_time):
        """Mark a node as inactive with temporal tracking.

        Args:
            node_idx: Index of node to remove
            visit_time: Current visitation time for temporal tracking
        """
        self.active[node_idx] = False
        self.visit_time[node_idx] = visit_time
        self.recently_visited.append(node_idx)

    def is_temporally_relevant(self, node_idx, current_time):
        """Check if a node is temporally relevant for re-evaluation.

        .

        Args:
            node_idx: Index of the node
            current_time: Current visitation time

        Returns:
            bool: True if node is temporally relevant
        """
        # Node is not relevant if it was recently visited
        if node_idx in self.recently_visited:
            return False

        # Node is not relevant if it was just removed
        return self.visit_time[node_idx] != current_time - 1

    def _compute_node_lower_bound(self, query_pos, node):
        """Compute minimum possible squared distance from query to any point in node.

        Args:
            query_pos: NumPy array [x, y] of query coordinates
            node: KDTreeNode to compute lower bound for

        Returns:
            float: Minimum possible squared distance to any point in the node
        """
        dx = 0.0
        if query_pos[0] < node.min_bound[0]:
            dx = node.min_bound[0] - query_pos[0]
        elif query_pos[0] > node.max_bound[0]:
            dx = query_pos[0] - node.max_bound[0]

        dy = 0.0
        if query_pos[1] < node.min_bound[1]:
            dy = node.min_bound[1] - query_pos[1]
        elif query_pos[1] > node.max_bound[1]:
            dy = query_pos[1] - node.max_bound[1]

        return dx * dx + dy * dy

    def _collect_candidates_from_node(self, node, candidates, distances, query_idx, max_candidates):
        """Collect active candidates from a node, considering temporal locality.

        Args:
            node: KDTreeNode to collect from
            candidates: List to append candidate indices to
            distances: List to append squared distances to
            query_idx: Index of query point
            max_candidates: Maximum number of candidates to collect
        """
        if node is None:
            return

        # Check if we've collected enough candidates
        if len(candidates) >= max_candidates:
            return

        if node.is_leaf:
            # Collect all points from this leaf node
            indices = node.point_indices
            active_mask = self.active[indices]

            if not np.any(active_mask):
                return

            active_indices = indices[active_mask]

            # Filter out temporally irrelevant nodes
            current_time = len(self.tour)
            relevant_mask = np.array([
                self.is_temporally_relevant(idx, current_time) for idx in active_indices
            ])

            if not np.any(relevant_mask):
                return

            relevant_indices = active_indices[relevant_mask]
            dists_sq = self.dist_sq_matrix[query_idx, relevant_indices]

            # Add all points to candidates
            for idx, dist_sq in zip(relevant_indices, dists_sq, strict=True):
                candidates.append(int(idx))
                distances.append(float(dist_sq))
        else:
            # Recursively collect from children
            self._collect_candidates_from_node(node.left, candidates, distances, query_idx, max_candidates)
            self._collect_candidates_from_node(node.right, candidates, distances, query_idx, max_candidates)

    def _phase1_quick_search(self, query_idx, query_pos, initial_k, max_nodes_to_visit=20):
        """Phase 1: Quick local search for nearest neighbor approximation.

        This phase performs a focused search in the immediate vicinity of the query point
        to get a quick approximation of the nearest neighbor. It explores only nearby
        nodes in the tree and collects a limited number of candidates.

        Args:
            query_idx: Index of query point
            query_pos: NumPy array [x, y] of query coordinates
            initial_k: Number of candidates to find
            max_nodes_to_visit: Maximum number of tree nodes to visit

        Returns:
            tuple: (candidates list, distances list)
        """
        candidates = []
        distances = []

        # Priority queue: (lower_bound_sq, node)
        pq = []
        visited_nodes = 0

        # Start with root node
        root_bound = self._compute_node_lower_bound(query_pos, self.root)
        heapq.heappush(pq, (root_bound, self.root))

        while pq and len(candidates) < initial_k and visited_nodes < max_nodes_to_visit:
            lower_bound_sq, node = heapq.heappop(pq)

            # Prune if lower bound is already worse than our best distance
            if distances and lower_bound_sq > distances[-1]:
                continue

            visited_nodes += 1

            if node.is_leaf:
                # Collect candidates from this leaf
                self._collect_candidates_from_node(node, candidates, distances, query_idx, initial_k * 2)
            else:
                # Add children to queue, prioritizing closer child
                if node.left is not None:
                    left_bound = self._compute_node_lower_bound(query_pos, node.left)
                    heapq.heappush(pq, (left_bound, node.left))

                if node.right is not None:
                    right_bound = self._compute_node_lower_bound(query_pos, node.right)
                    heapq.heappush(pq, (right_bound, node.right))

        # Sort candidates by distance
        if candidates:
            sorted_pairs = sorted(zip(distances, candidates, strict=True))
            distances, candidates = zip(*sorted_pairs, strict=True)
            return list(candidates[:initial_k]), list(distances[:initial_k])

        return [], []

    def _phase2_thorough_search(self, query_idx, query_pos, candidates, distances, k, best_dist_sq=None):
        """Phase 2: Thorough global search to refine the nearest neighbor.

        This phase performs a more exhaustive search of the entire tree to ensure
        we haven't missed a closer point. It uses the initial candidates' best distance
        to prune distant branches of the tree.

        Args:
            query_idx: Index of query point
            query_pos: NumPy array [x, y] of of query coordinates
            candidates: Existing candidates from phase 1
            distances: Existing distances from phase 1
            k: Number of neighbors to find
            best_dist_sq: Best distance found so far (for pruning)

        Returns:
            tuple: (candidates list, distances list) - refined results
        """
        if best_dist_sq is None and distances:
            best_dist_sq = distances[0]

        # Priority queue: (lower_bound_sq, node)
        pq = []

        # Start with root node
        root_bound = self._compute_node_lower_bound(query_pos, self.root)
        heapq.heappush(pq, (root_bound, self.root))

        nodes_visited = 0
        max_nodes_to_visit = min(200, self.n // 5)  # Limit thorough search

        while pq and nodes_visited < max_nodes_to_visit:
            lower_bound_sq, node = heapq.heappop(pq)

            # Prune if this node can't improve our result
            if best_dist_sq is not None and lower_bound_sq >= best_dist_sq:
                continue

            nodes_visited += 1

            if node.is_leaf:
                # Check all points in this leaf
                indices = node.point_indices
                active_mask = self.active[indices]

                if np.any(active_mask):
                    active_indices = indices[active_mask]

                    # Filter temporally irrelevant nodes
                    current_time = len(self.tour)
                    for idx in active_indices:
                        if self.is_temporally_relevant(idx, current_time):
                            dist_sq = self.dist_sq_matrix[query_idx, idx]

                            # Add to candidates if better than current worst
                            if len(candidates) < k or dist_sq < best_dist_sq:
                                candidates.append(int(idx))
                                distances.append(float(dist_sq))

                                # Sort and keep top k
                                sorted_pairs = sorted(zip(distances, candidates, strict=True))
                                distances, candidates = zip(*sorted_pairs, strict=True)
                                distances = list(distances[:k])
                                candidates = list(candidates[:k])

                                # Update best distance
                                if distances:
                                    best_dist_sq = distances[-1]
            else:
                # Add children to queue
                if node.left is not None:
                    left_bound = self._compute_node_lower_bound(query_pos, node.left)
                    if best_dist_sq is None or left_bound < best_dist_sq:
                        heapq.heappush(pq, (left_bound, node.left))

                if node.right is not None:
                    right_bound = self._compute_node_lower_bound(query_pos, node.right)
                    if best_dist_sq is None or right_bound < best_dist_sq:
                        heapq.heappush(pq, (right_bound, node.right))

        # Final sort to ensure order
        if candidates:
            sorted_pairs = sorted(zip(distances, candidates, strict=True))
            distances, candidates = zip(*sorted_pairs, strict=True)

        return list(candidates[:k]), list(distances[:k])

    def find_k_nearest_two_phase(self, query_idx, k, visit_time):
        """Find k nearest active nodes using two-phase search.

        Phase 1: Quick local search to get a good approximation
        Phase 2: Thorough global search to refine the result

        This two-phase approach balances speed and accuracy by first finding
        a quick local solution, then performing a more thorough search only
        when necessary.

        Args:
            query_idx: Index of query point
            k: Number of neighbors to find
            visit_time: Current visitation time for temporal tracking

        Returns:
            tuple: (list of candidate indices, list of squared distances)
        """
        query_pos = self.nodes[query_idx]

        # Phase 1: Quick local search
        # Search for more candidates initially to ensure good coverage
        phase1_k = min(k * 3, 20)  # Get more candidates in phase 1
        candidates, distances = self._phase1_quick_search(query_idx, query_pos, phase1_k)

        # Phase 2: Thorough global search to refine
        # Only do phase 2 if phase 1 found some candidates
        if candidates:
            best_dist_sq = distances[0] if distances else None

            # Skip phase 2 if we're very confident in phase 1 result
            # This happens when the nearest neighbor is relatively close
            if best_dist_sq is None or best_dist_sq > 0.01 * np.sum(self.global_range ** 2):
                candidates, distances = self._phase2_thorough_search(
                    query_idx, query_pos, candidates, distances, k, best_dist_sq
                )
        else:
            # Phase 1 found nothing, do exhaustive phase 2
            candidates, distances = self._phase2_thorough_search(
                query_idx, query_pos, [], [], k, None
            )

        # Update last nearest distance for adaptive behavior
        if distances:
            self.last_nearest_dist = distances[0]

        # Return top k
        return list(candidates[:k]), list(distances[:k])

    def bidirectional_local_search(self, query_idx, search_radius=None):
        """Perform bidirectional local search to find better connections.

        This searches both forward (unvisited nodes) and backward (recently visited)
        to detect if a better local minimum exists.

        Args:
            query_idx: Index of query point
            search_radius: Maximum distance for local search (auto-determined if None)

        Returns:
            int: Index of best local node found, or None if none found
        """
        # Auto-determine search radius based on last nearest distance
        if search_radius is None:
            if self.last_nearest_dist < np.inf:
                search_radius = np.sqrt(self.last_nearest_dist) * 2.0
            else:
                # Use a fraction of global range
                search_radius = np.sqrt(np.sum(self.global_range ** 2)) * 0.1

        best_node = None
        best_dist_sq = np.inf

        # Forward search: find closest active node
        if len(self.recently_visited) > 0:
            current_time = len(self.tour)
            for i in range(self.n):
                if self.active[i] and self.is_temporally_relevant(i, current_time):
                    dist_sq = self.dist_sq_matrix[query_idx, i]
                    if dist_sq <= search_radius * search_radius and dist_sq < best_dist_sq:
                        best_dist_sq = dist_sq
                        best_node = i

        # Backward search: check if we should connect to a recently visited node
        # (this can help avoid crossing paths)
        if len(self.recently_visited) >= 2:
            for recent_idx in list(self.recently_visited)[-3:]:  # Check last 3 visited
                if recent_idx != query_idx:
                    dist_sq = self.dist_sq_matrix[query_idx, recent_idx]
                    if dist_sq < best_dist_sq:
                        best_dist_sq = dist_sq
                        best_node = recent_idx

        return best_node


def hybrid_kdtree_two_phase_tsp(nodes):
    """TSP solver with KD-Tree hierarchical indexing and two-phase search.

    This algorithm combines hierarchical spatial indexing with a two-phase
    nearest neighbor search to build high-quality TSP tours efficiently.

    Key optimizations:
    1. K-means clustering for strategic starting point selection
    2. KD-Tree hierarchical spatial indexing for efficient neighbor queries
    3. Two-phase search: quick local approximation + thorough global refinement
    4. Temporal lazy deletion to optimize re-evaluation
    5. Bidirectional local search for better local connections
    6. Dynamic k-nearest neighbors based on tour progress

    Args:
        nodes: List of (x, y) coordinate tuples representing cities

    Returns:
        list: Tour as a list of node indices in visitation order
    """
    n = len(nodes)
    if n == 0:
        return []
    if n == 1:
        return [0]
    if n == 2:
        return [0, 1]

    # Convert to NumPy array for efficient operations
    nodes_array = np.array(nodes, dtype=np.float64)

    # For very small instances, use vectorized brute-force
    if n <= 50:
        unvisited = np.ones(n, dtype=bool)
        tour = [0]
        unvisited[0] = False
        current = 0

        for _ in range(n - 1):
            current_pos = nodes_array[current]
            diff = nodes_array[unvisited] - current_pos
            dists_sq = np.sum(diff * diff, axis=1)
            local_min_idx = np.argmin(dists_sq)

            unvisited_indices = np.nonzero(unvisited)[0]
            nearest = int(unvisited_indices[local_min_idx])

            tour.append(nearest)
            unvisited[nearest] = False
            current = nearest

        return tour

    # Step 1: Perform k-means clustering for strategic starting point selection
    clusterer = KMeansClusterer(nodes_array)
    centroids, labels = clusterer.fit()

    # Step 2: Choose starting city as the centroid closest to an extreme point
    mean_pos = np.mean(nodes_array, axis=0)
    dist_to_center = np.sum((nodes_array - mean_pos) ** 2, axis=1)
    extreme_idx = int(np.argmax(dist_to_center))

    # Find the nearest real city to the chosen centroid
    extreme_cluster = labels[extreme_idx]
    centroid = centroids[extreme_cluster]

    cluster_nodes = clusterer.get_cluster_nodes(extreme_cluster)
    centroid_dists = np.sum((nodes_array[cluster_nodes] - centroid) ** 2, axis=1)
    start_idx = int(cluster_nodes[np.argmin(centroid_dists)])

    # Step 3: Build KD-Tree spatial index with hierarchical structure
    # Adjust min_leaf_size based on problem size for optimal tree depth
    min_leaf_size = max(5, int(np.log(n)))
    spatial_index = KDTreeIndex(nodes_array, min_leaf_size=min_leaf_size)
    spatial_index.tour = []  # Attach tour reference for temporal tracking

    # Initialize tour and deactivate start
    tour = [start_idx]
    spatial_index.remove_node(start_idx, 0)

    current = start_idx
    remaining = n - 1
    visit_time = 1

    # Step 4: Build tour with two-phase k-NN search
    for _ in range(n - 1):
        # Dynamic k based on remaining cities:
        # - Early in tour: evaluate more candidates to explore
        # - Late in tour: use fewer candidates to stay efficient
        if remaining <= 5:
            k = remaining
        else:
            k = min(10, max(3, int(np.log(remaining) * 2.5)))
        # Find k nearest candidates using two-phase search
        candidates, distances = spatial_index.find_k_nearest_two_phase(current, k, visit_time)

        if not candidates:
            # Fallback: find any remaining active city
            for i in range(n):
                if spatial_index.active[i]:
                    candidates = [i]
                    distances = [spatial_index.dist_sq_matrix[current, i]]
                    break

        if not candidates:
            break

        # Step 5: Try bidirectional local search for better connection
        # Only perform this every few steps to balance quality and efficiency
        if remaining % 3 == 0 and len(tour) > 2 and distances:
            # Search radius based on current nearest distance
            search_radius = np.sqrt(max(distances[0], 1.0)) * 2.0
            local_best = spatial_index.bidirectional_local_search(current, search_radius)

            # Only use bidirectional result if it's significantly better
            if local_best is not None and local_best != candidates[0]:
                local_dist = spatial_index.dist_sq_matrix[current, local_best]
                if local_dist < distances[0] * 0.8:  # 20% improvement threshold
                    candidates.insert(0, local_best)
                    distances.insert(0, local_dist)

        # Select optimal candidate from k options
        # For now, pick the nearest (first in sorted list)
        nearest = candidates[0]

        tour.append(nearest)
        spatial_index.remove_node(nearest, visit_time)
        spatial_index.tour.append(nearest)  # Update tour in spatial index
        current = nearest
        remaining -= 1
        visit_time += 1

    return tour
# EVOLVE_END


def calculate_tour_length(nodes, tour):
    """Calculate the total length of a TSP tour.

    Args:
        nodes: List of (x, y) coordinate tuples
        tour: List of node indices representing the tour

    Returns:
        float: Total tour length (including return to start)
    """
    if len(tour) < 2:
        return 0.0

    total = 0.0
    nodes = np.array(nodes)

    # Distance between consecutive nodes in tour
    for i in range(len(tour) - 1):
        total += np.linalg.norm(nodes[tour[i]] - nodes[tour[i + 1]])

    # Return to start
    total += np.linalg.norm(nodes[tour[-1]] - nodes[tour[0]])

    return total


def solve(nodes):
    """Main TSP solving function that delegates to the evolved algorithm.

    Args:
        nodes: List of (x, y) coordinate tuples representing cities

    Returns:
        dict: Solution containing tour and tour length
    """
    # Call the evolved TSP algorithm
    tour = hybrid_kdtree_two_phase_tsp(nodes)

    # Calculate tour length for validation/monitoring
    tour_length = calculate_tour_length(nodes, tour)

    return {
        "tour": tour,
        "tour_length": tour_length,
    }


def main():
    """Main entry point for the TSP solver."""
    if len(sys.argv) < 2:
        print("Usage: python solve.py '<input_json>'")
        sys.exit(1)

    # Parse input
    input_json = sys.argv[1]
    try:
        input_data = json.loads(input_json)
    except json.JSONDecodeError:
        print("Error: Invalid JSON input")
        sys.exit(1)

    nodes = input_data.get("nodes", [])
    if not nodes:
        print("Error: No nodes provided")
        sys.exit(1)

    # Solve TSP
    result = solve(nodes)

    # Output result as JSON
    print(json.dumps(result))


if __name__ == "__main__":
    main()
