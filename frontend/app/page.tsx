"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type EventRecord = { id: string; platform: string; author_name: string; text: string; timestamp: string; analysis?: { sentiment?: string } };
type Snapshot = { live_events: number; active_topics: number; emerging_narratives: number; coordination_signals: number; mode: string };

export default function Dashboard() {
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [snapshot, setSnapshot] = useState<Snapshot>({ live_events: 0, active_topics: 0, emerging_narratives: 0, coordination_signals: 0, mode: "LIVE" });
  const [error, setError] = useState("");
  async function load() {
    try {
      const [eventsResponse, healthResponse] = await Promise.all([fetch(`${API}/events?limit=12`), fetch(`${API}/health`)]);
      if (!eventsResponse.ok || !healthResponse.ok) throw new Error();
      setEvents(await eventsResponse.json());
      const health = await healthResponse.json();
      setSnapshot((current) => ({ ...current, mode: health.mode }));
      setError("");
    } catch { setError("Live API is unavailable. Check that the backend is running on port 8000."); }
  }
  useEffect(() => { load(); }, []);
  return <main className="shell">
    <aside className="rail"><div className="brand"><span className="brand-mark">SX</span><span>IMPACT<span className="accent">R</span></span></div><div className="rail-label">WORKSPACE</div><nav><a className="active"><span>◈</span> Intelligence board</a><a href="#sources"><span>◌</span> Source health</a></nav><div className="rail-foot"><div className="secure-dot"/> Live mode active<div className="rail-note">Only verified source events are displayed.</div></div></aside>
    <section className="content"><header className="topbar"><div><div className="eyebrow">NATIONAL TECHNICAL RESEARCH ORGANISATION · SIH26152</div><h1>Social intelligence <span className="muted">/ live operations</span></h1></div><div className="top-actions"><span className="live-pill"><i/> LIVE SOURCES</span><button className="icon-button" title="Refresh data" onClick={load}>↻</button></div></header>
      {error && <div className="error-banner">{error}</div>}
      <div className="control-strip"><div><span className="strip-kicker">LIVE COLLECTION</span><strong>X + Telegram</strong><span className="strip-sub">Waiting for authorized source events</span></div><button className="primary" onClick={load}>Refresh sources</button></div>
      <div className="metric-grid">{[["Live events", snapshot.live_events], ["Active topics", snapshot.active_topics], ["Emerging narratives", snapshot.emerging_narratives], ["Coordination signals", snapshot.coordination_signals]].map(([label, value]) => <div className="metric cyan" key={label}><span>{label}</span><strong>{value}</strong><small>Live data only</small></div>)}</div>
      <div className="section-head"><div><span className="eyebrow">LIVE STREAM</span><h2>Current source activity</h2></div><span className="updated">No data is generated locally</span></div>
      <div className="three-col"><Panel title="Recent events" action="Live only"><div className="empty-state">{events.length ? events.map((event) => <div className="feed-row" key={event.id}><div className={`platform ${event.platform}`}>{event.platform === "telegram" ? "TG" : "X"}</div><div className="feed-body"><strong>{event.author_name} <em>· {event.platform}</em></strong><p>{event.text}</p><small>{new Date(event.timestamp).toLocaleString()}</small></div><div className={`sentiment ${event.analysis?.sentiment || "neutral"}`}>{event.analysis?.sentiment || "—"}</div></div>) : "No live events available."}</div></Panel><Panel title="Analysis" action="Live only"><div className="empty-state">Analysis will appear after live events arrive.</div></Panel><Panel title="Signals" action="Live only"><div className="empty-state">No live signals available.</div></Panel></div>
      <div className="section-head" id="sources"><div><span className="eyebrow">SOURCE HEALTH</span><h2>Authorized sources</h2></div></div><div className="source-footer">{["X", "Telegram"].map((source) => <span key={source} className="source"><i className="hollow-dot"/>{source} <small>CHECK API STATUS</small></span>)}</div>
    </section>
  </main>;
}
function Panel({ title, action, children }: { title: string; action: string; children: React.ReactNode }) { return <section className="panel"><div className="panel-head"><h3>{title}</h3><span>{action}</span></div>{children}</section>; }
