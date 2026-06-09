import { useEffect, useRef } from "react"

interface Island {
  x: number
  y: number
  radius: number
  nodes: Node[]
}

interface Node {
  x: number
  y: number
  vx: number
  vy: number
  baseX: number
  baseY: number
  radius: number
  opacity: number
  phase: number
}

interface Migrant {
  x: number
  y: number
  targetX: number
  targetY: number
  progress: number
  speed: number
  opacity: number
}

interface ColorPalette {
  bg: string
  node: [number, number, number]
  glow: string
  trail: [number, number, number]
  center: [number, number, number]
}

const DARK_PALETTE: ColorPalette = {
  bg: "#060b1a",
  node: [0, 212, 255],
  glow: "#00d4ff",
  trail: [96, 239, 255],
  center: [0, 136, 255],
}

const LIGHT_PALETTE: ColorPalette = {
  bg: "#f8fafc",
  node: [37, 99, 235],
  glow: "#2563eb",
  trail: [59, 130, 246],
  center: [37, 99, 235],
}

function createIslands(w: number, h: number): Island[] {
  const positions = [
    { x: 0.15, y: 0.2 },
    { x: 0.8, y: 0.15 },
    { x: 0.5, y: 0.5 },
    { x: 0.2, y: 0.8 },
    { x: 0.85, y: 0.75 },
  ]

  return positions.map((pos) => {
    const cx = pos.x * w
    const cy = pos.y * h
    const r = Math.min(w, h) * 0.12
    const nodeCount = 8 + Math.floor(Math.random() * 5)
    const nodes: Node[] = []

    for (let i = 0; i < nodeCount; i++) {
      const angle = Math.random() * Math.PI * 2
      const dist = Math.random() * r
      const nx = cx + Math.cos(angle) * dist
      const ny = cy + Math.sin(angle) * dist
      nodes.push({
        x: nx,
        y: ny,
        baseX: nx,
        baseY: ny,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        radius: 1.5 + Math.random() * 2,
        opacity: 0.4 + Math.random() * 0.6,
        phase: Math.random() * Math.PI * 2,
      })
    }

    return { x: cx, y: cy, radius: r, nodes }
  })
}

function spawnMigrant(islands: Island[]): Migrant {
  const from = islands[Math.floor(Math.random() * islands.length)]
  let to = islands[Math.floor(Math.random() * islands.length)]
  while (to === from && islands.length > 1) {
    to = islands[Math.floor(Math.random() * islands.length)]
  }
  const srcNode = from.nodes[Math.floor(Math.random() * from.nodes.length)]
  const dstNode = to.nodes[Math.floor(Math.random() * to.nodes.length)]
  return {
    x: srcNode.x,
    y: srcNode.y,
    targetX: dstNode.x,
    targetY: dstNode.y,
    progress: 0,
    speed: 0.002 + Math.random() * 0.003,
    opacity: 0.6 + Math.random() * 0.4,
  }
}

interface IslandBackgroundProps {
  variant?: "dark" | "light"
}

export default function IslandBackground({
  variant = "dark",
}: IslandBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const palette = variant === "light" ? LIGHT_PALETTE : DARK_PALETTE
    const opacityScale = variant === "light" ? 0.5 : 1

    let animId: number
    let islands: Island[] = []
    let migrants: Migrant[] = []
    let time = 0

    const resize = () => {
      const dpr = window.devicePixelRatio || 1
      canvas.width = window.innerWidth * dpr
      canvas.height = window.innerHeight * dpr
      canvas.style.width = `${window.innerWidth}px`
      canvas.style.height = `${window.innerHeight}px`
      ctx.scale(dpr, dpr)
      islands = createIslands(window.innerWidth, window.innerHeight)
      migrants = []
      for (let i = 0; i < 3; i++) migrants.push(spawnMigrant(islands))
    }

    resize()
    window.addEventListener("resize", resize)

    const maxConnDist = Math.min(window.innerWidth, window.innerHeight) * 0.15
    const [nr, ng, nb] = palette.node
    const [tr, tg, tb] = palette.trail
    const [cr, cg, cb] = palette.center

    const draw = () => {
      const w = window.innerWidth
      const h = window.innerHeight
      time += 0.01

      ctx.clearRect(0, 0, w, h)

      for (const island of islands) {
        for (let i = 0; i < island.nodes.length; i++) {
          for (let j = i + 1; j < island.nodes.length; j++) {
            const a = island.nodes[i]
            const b = island.nodes[j]
            const dx = a.x - b.x
            const dy = a.y - b.y
            const dist = Math.sqrt(dx * dx + dy * dy)
            if (dist < maxConnDist) {
              const alpha = (1 - dist / maxConnDist) * 0.15 * opacityScale
              ctx.beginPath()
              ctx.moveTo(a.x, a.y)
              ctx.lineTo(b.x, b.y)
              ctx.strokeStyle = `rgba(${nr}, ${ng}, ${nb}, ${alpha})`
              ctx.lineWidth = 0.5
              ctx.stroke()
            }
          }
        }
      }

      for (const island of islands) {
        for (const node of island.nodes) {
          node.phase += 0.008 + Math.random() * 0.002
          node.x =
            node.baseX +
            Math.sin(node.phase) * 8 +
            Math.cos(node.phase * 0.7) * 5
          node.y =
            node.baseY +
            Math.cos(node.phase) * 8 +
            Math.sin(node.phase * 0.6) * 5

          const dx = node.x - island.x
          const dy = node.y - island.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist > island.radius * 1.2) {
            node.baseX += (island.x - node.baseX) * 0.01
            node.baseY += (island.y - node.baseY) * 0.01
          }

          const pulseAlpha =
            (0.3 + 0.2 * Math.sin(time * 2 + node.phase)) * opacityScale
          ctx.save()
          ctx.shadowColor = palette.glow
          ctx.shadowBlur = 12
          ctx.beginPath()
          ctx.arc(node.x, node.y, node.radius * 2, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(${nr}, ${ng}, ${nb}, ${pulseAlpha * 0.3})`
          ctx.fill()
          ctx.restore()

          ctx.beginPath()
          ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(${nr}, ${ng}, ${nb}, ${node.opacity * (0.6 + 0.4 * Math.sin(time + node.phase)) * opacityScale})`
          ctx.fill()
        }
      }

      for (const island of islands) {
        const gradient = ctx.createRadialGradient(
          island.x,
          island.y,
          0,
          island.x,
          island.y,
          island.radius,
        )
        gradient.addColorStop(
          0,
          `rgba(${cr}, ${cg}, ${cb}, ${0.03 * opacityScale})`,
        )
        gradient.addColorStop(0, `rgba(${cr}, ${cg}, ${cb}, 0)`)
        ctx.beginPath()
        ctx.arc(island.x, island.y, island.radius, 0, Math.PI * 2)
        ctx.fillStyle = gradient
        ctx.fill()
      }

      for (let i = migrants.length - 1; i >= 0; i--) {
        const m = migrants[i]
        m.progress += m.speed

        const t = m.progress
        const midX = (m.x + m.targetX) / 2 + (m.targetY - m.y) * 0.2
        const midY = (m.y + m.targetY) / 2 - (m.targetX - m.x) * 0.2
        const cx =
          (1 - t) * (1 - t) * m.x + 2 * (1 - t) * t * midX + t * t * m.targetX
        const cy =
          (1 - t) * (1 - t) * m.y + 2 * (1 - t) * t * midY + t * t * m.targetY

        const fadeAlpha =
          m.opacity *
          (t < 0.1 ? t / 0.1 : t > 0.9 ? (1 - t) / 0.1 : 1) *
          opacityScale

        ctx.save()
        ctx.shadowColor = palette.glow
        ctx.shadowBlur = 8
        ctx.beginPath()
        ctx.arc(cx, cy, 2, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${tr}, ${tg}, ${tb}, ${fadeAlpha})`
        ctx.fill()
        ctx.restore()

        if (m.progress >= 1) {
          migrants[i] = spawnMigrant(islands)
        }
      }

      if (migrants.length < 5 && Math.random() < 0.005) {
        migrants.push(spawnMigrant(islands))
      }

      animId = requestAnimationFrame(draw)
    }

    animId = requestAnimationFrame(draw)

    const onVisibilityChange = () => {
      if (document.hidden) {
        cancelAnimationFrame(animId)
      } else {
        animId = requestAnimationFrame(draw)
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange)

    return () => {
      window.removeEventListener("resize", resize)
      document.removeEventListener("visibilitychange", onVisibilityChange)
      cancelAnimationFrame(animId)
    }
  }, [variant])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 z-0"
      style={{
        background: variant === "light" ? LIGHT_PALETTE.bg : DARK_PALETTE.bg,
      }}
    />
  )
}
