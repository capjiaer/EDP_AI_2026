/**
 * Layout a DAG using BFS topological sort with grid positioning.
 *
 * @param {Array<{id: string}>} rawNodes
 * @param {Array<{source: string, target: string}>} edges
 * @param {object} options
 * @param {number} options.horizontalSpacing — x spacing (default 180)
 * @param {number} options.verticalSpacing   — y spacing per level (default 120)
 * @returns {Map<string, {x: number, y: number}>}
 */
export function layoutGraph(rawNodes, edges, options = {}) {
  const hs = options.horizontalSpacing ?? 180
  const vs = options.verticalSpacing ?? 120

  // Build downstream map and in-degree
  const downstream = {}
  const inDegree = {}
  for (const n of rawNodes) {
    downstream[n.id] = []
    inDegree[n.id] = 0
  }
  for (const e of edges) {
    if (downstream[e.source]) {
      downstream[e.source].push(e.target)
    }
    inDegree[e.target] = (inDegree[e.target] || 0) + 1
  }

  // BFS to assign levels
  const levels = {}
  const queue = rawNodes.filter(n => inDegree[n.id] === 0).map(n => n.id)
  for (const id of queue) {
    levels[id] = 0
  }
  let idx = 0
  while (idx < queue.length) {
    const current = queue[idx++]
    for (const child of (downstream[current] || [])) {
      levels[child] = Math.max(levels[child] || 0, (levels[current] || 0) + 1)
      inDegree[child]--
      if (inDegree[child] === 0) {
        queue.push(child)
      }
    }
  }

  // Group by level for positioning
  const levelGroups = {}
  for (const [id, lvl] of Object.entries(levels)) {
    if (!levelGroups[lvl]) levelGroups[lvl] = []
    levelGroups[lvl].push(id)
  }
  const positions = new Map()
  for (const [lvl, ids] of Object.entries(levelGroups)) {
    ids.forEach((id, i) => {
      positions.set(id, { x: i * hs, y: Number(lvl) * vs })
    })
  }

  return positions
}
