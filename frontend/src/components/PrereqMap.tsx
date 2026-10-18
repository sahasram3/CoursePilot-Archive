import { useMemo, useState } from "react";
import type { Plan, PlanResponse, RequirementStatus } from "../types";

const NODE_W = 150, NODE_H = 46, COL_W = 182, ROW_H = 58, TOP = 34, PAD = 12;

interface Node { code: string; title: string; col: number; row: number; done: boolean }

/** Columns = starting credit + each term; edges = the courses that actually meet
 *  each planned course's prerequisites in this plan (from the solver output). */
export function PrereqMap({ response, plan, onShow }: { response: PlanResponse; plan: Plan; onShow: (c: string) => void }) {
  const [hover, setHover] = useState<string | null>(null);

  const { nodes, edges, columns } = useMemo(() => {
    const planned = plan.terms.flatMap((t, i) => t.courses.map((c) => ({ ...c, col: i + 1 })));
    const referenced = new Set(planned.flatMap((c) => c.satisfied_by));
    const used = new Set(collectCourses(Object.values(plan.requirements).flat()));
    const doneNodes = response.completed_courses
      .filter((c) => c.code && (referenced.has(c.code) || used.has(c.code)))
      .map((c, row) => ({ code: c.code!, title: c.title, col: 0, row, done: true }));
    const rows = new Map<number, number>();
    const plannedNodes: Node[] = planned.map((c) => {
      const row = rows.get(c.col) ?? 0;
      rows.set(c.col, row + 1);
      return { code: c.code, title: c.title, col: c.col, row, done: false };
    });
    const all = [...doneNodes, ...plannedNodes];
    const byCode = new Map(all.map((n) => [n.code, n]));
    const edgeList = planned.flatMap((c) => c.satisfied_by.filter((s) => byCode.has(s)).map((s) => [s, c.code] as const));
    return { nodes: all, edges: edgeList, columns: ["Starting credit", ...plan.terms.map((t) => t.term)] };
  }, [plan, response]);

  const related = useMemo(() => {
    if (!hover) return null;
    const out = new Set([hover]);
    const walk = (code: string, dir: 0 | 1) => {
      for (const e of edges) if (e[dir] === code && !out.has(e[1 - dir])) { out.add(e[1 - dir]); walk(e[1 - dir], dir); }
    };
    walk(hover, 0);
    walk(hover, 1);
    return out;
  }, [hover, edges]);

  const pos = (n: Node) => ({ x: PAD + n.col * COL_W, y: TOP + n.row * ROW_H });
  const byCode = new Map(nodes.map((n) => [n.code, n]));
  const height = TOP + Math.max(1, ...nodes.map((n) => n.row + 1)) * ROW_H + PAD;
  const width = PAD * 2 + columns.length * COL_W - (COL_W - NODE_W);

  if (nodes.length === 0) return <p className="muted panel">No program courses to map.</p>;
  return (
    <section className="panel map-panel">
      <p className="hint">Arrows show which course satisfies each prerequisite in this plan. Hover or focus a course to trace its chain; click for details.</p>
      <div className="map-scroll">
        <svg width={width} height={height} role="img" aria-label="Prerequisite map of the plan">
          {columns.map((label, i) => (
            <text key={label} x={PAD + i * COL_W} y={18} className="map-col">{label}</text>
          ))}
          {edges.map(([from, to]) => {
            const a = pos(byCode.get(from)!), b = pos(byCode.get(to)!);
            const x1 = a.x + NODE_W, y1 = a.y + NODE_H / 2, x2 = b.x, y2 = b.y + NODE_H / 2;
            const mid = (x1 + x2) / 2;
            const lit = related ? related.has(from) && related.has(to) : false;
            return <path key={`${from}-${to}`} d={`M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2 - 4},${y2}`}
                         className={`map-edge ${lit ? "lit" : related ? "dim" : ""}`} markerEnd="url(#arrow)" />;
          })}
          <defs>
            <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L8,4 L0,8 z" className="map-arrow" />
            </marker>
          </defs>
          {nodes.map((n) => {
            const { x, y } = pos(n);
            const dim = related && !related.has(n.code);
            return (
              <g key={n.code} transform={`translate(${x},${y})`} tabIndex={0} role="button" aria-label={`${n.code} ${n.title}`}
                 className={`map-node ${n.done ? "done" : ""} ${dim ? "dim" : ""} ${hover === n.code ? "hot" : ""}`}
                 onMouseEnter={() => setHover(n.code)} onMouseLeave={() => setHover(null)}
                 onFocus={() => setHover(n.code)} onBlur={() => setHover(null)}
                 onClick={() => onShow(n.code)} onKeyDown={(e) => e.key === "Enter" && onShow(n.code)}>
                <rect width={NODE_W} height={NODE_H} rx={8} />
                <text x={10} y={19} className="map-code">{n.code}</text>
                <text x={10} y={35} className="map-title">{n.title.length > 22 ? n.title.slice(0, 21) + "…" : n.title}</text>
              </g>
            );
          })}
        </svg>
      </div>
    </section>
  );
}

function collectCourses(nodes: RequirementStatus[]): string[] {
  return nodes.flatMap((n) => [...n.courses.map((c) => c.code), ...collectCourses(n.children)]);
}
