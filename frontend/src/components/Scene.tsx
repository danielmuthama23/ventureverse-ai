import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, OrbitControls, Stars } from "@react-three/drei";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { AgentStatus, Claim, Mission, Mode, World } from "../lib/types";

export type Pick = { kind: "agent" | "claim" | "competitor" | "segment" | "city"; id: string };
interface Props { world: World; mission: Mission | null; mode: Mode; onPick: (p: Pick) => void }

const STATUS_COLOR = { verified: "#2fe6a8", estimate: "#ffc04d", hypothesis: "#ff6384" } as const;
const TILT_X = [0.2, -0.5, 0.9, -0.9, 0.4, -0.25, 1.15];

function latLon(lat: number, lon: number, r: number) {
  const ph = ((90 - lat) * Math.PI) / 180, th = ((lon + 180) * Math.PI) / 180;
  return new THREE.Vector3(-r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph), r * Math.sin(ph) * Math.sin(th));
}
/** Deterministic pseudo-random in [0,1) from a string, so orbs keep their place across renders. */
function rnd(seed: string, salt: number) {
  let h = 2166136261 ^ salt;
  for (let i = 0; i < seed.length; i++) h = Math.imul(h ^ seed.charCodeAt(i), 16777619);
  return ((h >>> 0) % 100000) / 100000;
}
const hover = (on: boolean) => { document.body.style.cursor = on ? "pointer" : ""; };
const Label = ({ children, color }: { children: React.ReactNode; color?: string }) => (
  <Html center zIndexRange={[5, 0]} style={{ pointerEvents: "none" }}>
    <div className="lbl" style={{ position: "static", borderColor: color, transform: "translateY(-26px)" }}>{children}</div>
  </Html>
);

function Satellite({ index, agent, status, onPick, running, dispatchProgress }: { index: number; agent: World["agents"][number]; status: AgentStatus; onPick: Props["onPick"]; running: string | null; dispatchProgress: Record<string, number> }) {
  const mesh = useRef<THREE.Mesh>(null!);
  const ringRef = useRef<THREE.Mesh>(null!);
  const mat = useRef<THREE.MeshStandardMaterial>(null!);
  const radius = 5.5 + (index % 3) * 0.9;
  const speed = 0.1 + (index % 4) * 0.028;
  const phase = useRef((index * Math.PI * 2) / 7);
  const active = running === agent.id || status === "running";
  const progress = Math.round(dispatchProgress[agent.id] ?? (status === "done" ? 100 : 0));
  useFrame((_, dt) => {
    phase.current += dt * speed * (active ? 3 : 1);
    mesh.current.position.set(Math.cos(phase.current) * radius, 0, Math.sin(phase.current) * radius);
    mesh.current.rotation.y += dt * (active ? 6 : 0.8);
    if (ringRef.current) ringRef.current.rotation.z += dt * (active ? 4 : 1.2);
    const target = active ? 1.3 : status === "done" ? 0.85 : status === "ready" ? 0.6 : 0.12;
    mat.current.emissiveIntensity += (target - mat.current.emissiveIntensity) * Math.min(1, dt * 6);
  });
  const ring = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let k = 0; k <= 96; k++) { const q = (k / 96) * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(q) * radius, 0, Math.sin(q) * radius)); }
    return new THREE.BufferGeometry().setFromPoints(pts);
  }, [radius]);
  return (
    <group rotation={[TILT_X[index] ?? 0, 0, index * 0.45]}>
      <line>
        <primitive object={ring} attach="geometry" />
        <lineBasicMaterial color={agent.color} transparent opacity={0.16} />
      </line>
      <mesh ref={mesh} onClick={(e) => { e.stopPropagation(); onPick({ kind: "agent", id: agent.id }); }} onPointerOver={() => hover(true)} onPointerOut={() => hover(false)}>
        <octahedronGeometry args={[0.4]} />
        <meshStandardMaterial ref={mat} color={agent.color} emissive={agent.color} emissiveIntensity={0.3} roughness={0.35} metalness={0.3} />
        {active && (
          <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[0.8, 0.04, 12, 64]} />
            <meshBasicMaterial color={agent.color} transparent opacity={0.9} />
          </mesh>
        )}
        {status === "done" && (
          <mesh><torusGeometry args={[0.62, 0.035, 8, 36]} /><meshBasicMaterial color="#2fe6a8" /></mesh>
        )}
        <Label color={agent.color}>{`${agent.name.split(" ")[0]}${progress > 0 ? ` ${progress}%` : ""}`}</Label>
      </mesh>
    </group>
  );
}

function Orb({ claim, onPick }: { claim: Claim; onPick: Props["onPick"] }) {
  const ref = useRef<THREE.Mesh>(null!);
  const pos = useMemo(() => {
    const th = rnd(claim.id, 1) * Math.PI * 2, ph = Math.acos(2 * rnd(claim.id, 2) - 1), r = 3.9 + rnd(claim.id, 3) * 0.8;
    return new THREE.Vector3(r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph), r * Math.sin(ph) * Math.sin(th));
  }, [claim.id]);
  const color = claim.verdict ? STATUS_COLOR[claim.verdict.truth] : "#8aa0ff";
  useFrame((_, dt) => { const s = ref.current.scale.x; ref.current.scale.setScalar(s + (1 - s) * Math.min(1, dt * 4)); });
  return (
    <mesh ref={ref} position={pos} scale={0.01} onClick={(e) => { e.stopPropagation(); onPick({ kind: "claim", id: claim.id }); }} onPointerOver={() => hover(true)} onPointerOut={() => hover(false)}>
      <sphereGeometry args={[0.13, 14, 14]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.9} />
    </mesh>
  );
}

function CommandCenter({ world, mission, onPick, running, dispatchProgress }: Omit<Props, "mode"> & { running: string | null; dispatchProgress: Record<string, number> }) {
  const group = useRef<THREE.Group>(null!);
  const core = useRef<THREE.Mesh>(null!);
  const q = useMemo(() => {
    const n = world.cities["Nairobi"];
    const target = new THREE.Vector3(Math.sin(0.6) * Math.sin(1.3), Math.cos(1.3), Math.cos(0.6) * Math.sin(1.3));
    return new THREE.Quaternion().setFromUnitVectors(latLon(n.lat, n.lon, 1).normalize(), target.normalize());
  }, [world]);
  useFrame((_, dt) => { core.current.rotation.y += dt * 0.5; group.current.rotation.y += dt * 0.02; });
  const top = mission?.recommendation?.city;
  const status = (id: string): AgentStatus => mission?.agents.find((a) => a.id === id)?.status ?? "locked";
  return (
    <group ref={group}>
      <mesh ref={core}><icosahedronGeometry args={[0.9, 1]} /><meshStandardMaterial color="#6a7dff" emissive="#6a4dff" emissiveIntensity={1.1} roughness={0.4} metalness={0.2} /></mesh>
      <mesh><icosahedronGeometry args={[3.7, 1]} /><meshBasicMaterial color="#6a4dff" wireframe transparent opacity={0.12} /></mesh>
      <group quaternion={q}>
        <mesh><sphereGeometry args={[3.12, 40, 28]} /><meshBasicMaterial color="#0a1030" transparent opacity={0.6} /></mesh>
        <mesh><sphereGeometry args={[3.2, 36, 24]} /><meshBasicMaterial color="#2f46a8" wireframe transparent opacity={0.3} /></mesh>
        {Object.entries(world.cities).map(([name, c]) => {
          const score = mission?.recommendation?.scores[name];
          return (
            <mesh key={name} position={latLon(c.lat, c.lon, 3.22)}>
              <sphereGeometry args={[0.07 + (score ?? 0) / 100 * 0.12, 12, 12]} />
              <meshBasicMaterial color={name === top ? "#b48cff" : "#7aa2ff"} />
            </mesh>
          );
        })}
      </group>
      {world.agents.map((a, i) => <Satellite key={a.id} index={i} agent={a} status={status(a.id)} onPick={onPick} running={running} dispatchProgress={dispatchProgress} />)}
      {mission?.claims.map((c) => <Orb key={c.id} claim={c} onPick={onPick} />)}
    </group>
  );
}

function Galaxy({ world, visible, onPick }: { world: World; visible: boolean; onPick: Props["onPick"] }) {
  const refs = useRef<Record<string, THREE.Mesh | null>>({});
  const pos = useMemo(() => Object.fromEntries(world.competitors.map((c) => [c.id, new THREE.Vector3(...c.pos)])), [world]);
  const lines = useMemo(() => {
    const pairs: [THREE.Vector3, THREE.Vector3][] = world.competitors.map((c) => [new THREE.Vector3(), pos[c.id]]);
    world.competitor_edges.forEach(([a, b]) => pairs.push([pos[a], pos[b]]));
    return pairs.map(([a, b]) => new THREE.BufferGeometry().setFromPoints([a, b]));
  }, [world, pos]);
  useFrame((_, dt) => Object.values(refs.current).forEach((m) => { if (m) { const t = visible ? 1 : 0.001; m.scale.setScalar(m.scale.x + (t - m.scale.x) * Math.min(1, dt * 4)); } }));
  return (
    <group>
      <mesh><sphereGeometry args={[0.55, 24, 24]} /><meshStandardMaterial color="#4a86ff" emissive="#4a86ff" emissiveIntensity={0.9} /><Label>Your venture</Label></mesh>
      {visible && lines.map((g, i) => <line key={i}><primitive object={g} attach="geometry" /><lineBasicMaterial color="#8b5cf6" transparent opacity={0.4} /></line>)}
      {world.competitors.map((c) => {
        const col = new THREE.Color("#4a5a99").lerp(new THREE.Color("#b06bff"), c.overlap);
        return (
          <mesh key={c.id} ref={(m) => { refs.current[c.id] = m; }} position={c.pos} scale={0.001}
            onClick={(e) => { e.stopPropagation(); onPick({ kind: "competitor", id: c.id }); }} onPointerOver={() => hover(true)} onPointerOut={() => hover(false)}>
            <sphereGeometry args={[0.3 + 0.35 * c.strength, 20, 20]} />
            <meshStandardMaterial color={col} emissive={col} emissiveIntensity={0.5} />
            {visible && <Label>{c.name}</Label>}
          </mesh>
        );
      })}
    </group>
  );
}

function Cluster({ seg, visible, onPick }: { seg: World["segments"][number]; visible: boolean; onPick: Props["onPick"] }) {
  const ref = useRef<THREE.Group>(null!);
  const geo = useMemo(() => {
    const n = Math.round(140 + seg.size * 520), p = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const r = (0.4 + seg.size * 1.1) * Math.pow(rnd(seg.id, i * 3), 0.6), th = rnd(seg.id, i * 3 + 1) * Math.PI * 2, ph = Math.acos(2 * rnd(seg.id, i * 3 + 2) - 1);
      p.set([r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph), r * Math.sin(ph) * Math.sin(th)], i * 3);
    }
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(p, 3)); return g;
  }, [seg]);
  useFrame((_, dt) => { const s = ref.current.scale.x, t = visible ? 1 : 0.001; ref.current.scale.setScalar(s + (t - s) * Math.min(1, dt * 3)); ref.current.rotation.y += dt * 0.15; });
  return (
    <group ref={ref} position={seg.pos} scale={0.001}>
      <points geometry={geo}><pointsMaterial color={seg.col} size={0.09} transparent opacity={0.9} depthWrite={false} blending={THREE.AdditiveBlending} /></points>
      <mesh onClick={(e) => { e.stopPropagation(); onPick({ kind: "segment", id: seg.id }); }} onPointerOver={() => hover(true)} onPointerOut={() => hover(false)}>
        <sphereGeometry args={[0.5 + seg.size * 1.1, 10, 8]} /><meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
      {visible && <Label color={seg.col}>{seg.name}</Label>}
    </group>
  );
}

function Pillar({ name, lat, lon, score, top, onPick }: { name: string; lat: number; lon: number; score: number | undefined; top: boolean; onPick: Props["onPick"] }) {
  const ref = useRef<THREE.Mesh>(null!);
  const target = Math.max(0.2, ((score ?? 0) / 100) * 3.6);
  useFrame((_, dt) => { ref.current.scale.y += (target - ref.current.scale.y) * Math.min(1, dt * 3); });
  return (
    <mesh ref={ref} position={[(lon - 37.2) * 2.4, 0, -(lat + 1.6) * 2.4]} scale={[1, 0.2, 1]}
      onClick={(e) => { e.stopPropagation(); onPick({ kind: "city", id: name }); }} onPointerOver={() => hover(true)} onPointerOut={() => hover(false)}>
      <boxGeometry args={[0.9, 1, 0.9]} />
      <meshStandardMaterial color={top ? "#9a6bff" : "#3a5fc8"} emissive={top ? "#7a4dff" : "#2a46a0"} emissiveIntensity={0.6} roughness={0.4} />
      <Html position={[0, 0.5, 0]} center style={{ pointerEvents: "none" }}>
        <div className="lbl" style={{ position: "static", transform: "translateY(-14px)" }}>{name} {score ?? "—"}</div>
      </Html>
    </mesh>
  );
}

const PRESET: Record<Mode, { pos: [number, number, number]; target: [number, number, number] }> = {
  command: { pos: [7, 3.5, 14], target: [0, 0, 0] },
  competitors: { pos: [4.5, 3, 11], target: [0, 0, 0] },
  customers: { pos: [3.5, 2.5, 11], target: [0, 0, 0] },
  radar: { pos: [2, 11, 17], target: [1.5, 0.8, 1.5] },
};

function CameraRig({ mode }: { mode: Mode }) {
  const { camera, controls } = useThree();
  const t = useRef(0);
  const last = useRef<Mode | null>(null);
  useFrame((_, dt) => {
    if (last.current !== mode) { last.current = mode; t.current = 0; }
    if (t.current >= 1) return;
    t.current = Math.min(1, t.current + dt * 1.2);
    const p = PRESET[mode], k = Math.min(1, dt * 5);
    camera.position.lerp(new THREE.Vector3(...p.pos), k);
    const oc = controls as unknown as { target: THREE.Vector3; update: () => void } | null;
    if (oc) { oc.target.lerp(new THREE.Vector3(...p.target), k); oc.update(); }
  });
  return null;
}

export default function Scene({ world, mission, mode, onPick, running, dispatchProgress }: Props & { running: string | null; dispatchProgress: Record<string, number> }) {
  const [ready] = useState(() => typeof window !== "undefined");
  const done = (id: string) => mission?.agents.find((a) => a.id === id)?.status === "done";
  const top = mission?.recommendation?.city;
  if (!ready) return null;
  return (
    <Canvas camera={{ position: PRESET.command.pos, fov: 50 }} dpr={[1, 2]} gl={{ antialias: true }}>
      <ambientLight intensity={0.9} />
      <pointLight position={[9, 6, 9]} intensity={90} color="#4a86ff" />
      <pointLight position={[-9, -5, -7]} intensity={90} color="#9a6bff" />
      <Stars radius={90} depth={40} count={900} factor={3} fade speed={0.3} />
      <OrbitControls makeDefault enablePan={false} minDistance={6} maxDistance={28} />
      <CameraRig mode={mode} />
      {mode === "command" && <CommandCenter world={world} mission={mission} onPick={onPick} running={running} dispatchProgress={dispatchProgress} />}
      {mode === "competitors" && <Galaxy world={world} visible={done("competitor")} onPick={onPick} />}
      {mode === "customers" && world.segments.map((s) => <Cluster key={s.id} seg={s} visible={done("customer")} onPick={onPick} />)}
      {mode === "radar" && (
        <group>
          <gridHelper args={[16, 16, "#2a3a7a", "#18224a"]} />
          {Object.entries(world.cities).map(([name, c]) => (
            <Pillar key={name} name={name} lat={c.lat} lon={c.lon} score={mission?.recommendation?.scores[name]} top={name === top} onPick={onPick} />
          ))}
        </group>
      )}
    </Canvas>
  );
}
