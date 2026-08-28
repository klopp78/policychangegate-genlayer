"use client";

import { useState } from "react";
import { POLICY_CHANGE_GATE_ADDRESS, readAssessment, readPolicy, writeGate, type WalletAddress } from "@/lib/genlayer";

declare global { interface Window { ethereum?: { request(args: { method: string }): Promise<unknown> } } }
type Status = "ready" | "working" | "accepted" | "error";
const explorer = `https://explorer-studio.genlayer.com/address/${POLICY_CHANGE_GATE_ADDRESS}`;
const github = "https://github.com/klopp78/policychangegate-genlayer";
const text = (value: unknown) => typeof value === "string" ? value : JSON.stringify(value, null, 2);

export default function Home() {
  const [wallet, setWallet] = useState<WalletAddress | null>(null);
  const [status, setStatus] = useState<Status>("ready");
  const [message, setMessage] = useState("Connect a Studio wallet to create challengeable policy-change records.");
  const [policyUrl, setPolicyUrl] = useState("https://docs.genlayer.com");
  const [rules, setRules] = useState("Owner may finalize only an unchallenged consensus-approved change; challenges require independent evidence.");
  const [policyId, setPolicyId] = useState("policy-1");
  const [candidateUrl, setCandidateUrl] = useState("https://docs.genlayer.com/developers");
  const [assessmentId, setAssessmentId] = useState("");
  const [challengeUrl, setChallengeUrl] = useState("https://docs.genlayer.com/developers/intelligent-contracts");
  const [record, setRecord] = useState("");
  const fail = (error: unknown) => { setStatus("error"); setMessage(error instanceof Error ? error.message : "The contract call did not complete."); };
  async function connect() {
    if (!window.ethereum) return fail("No browser wallet was detected.");
    try { setStatus("working"); const accounts = await window.ethereum.request({ method: "eth_requestAccounts" }) as string[]; if (!accounts[0]) throw new Error("Wallet did not return an account."); setWallet(accounts[0] as WalletAddress); setStatus("ready"); setMessage("Wallet connected. Reads and consensus writes are ready."); } catch (error) { fail(error); }
  }
  async function read(kind: "policy" | "assessment") {
    try { setStatus("working"); const item = kind === "policy" ? await readPolicy(policyId, wallet ?? undefined) : await readAssessment(assessmentId, wallet ?? undefined); setRecord(text(item)); setStatus("ready"); setMessage(`${kind === "policy" ? "Policy" : "Assessment"} loaded directly from Studio contract storage.`); } catch (error) { fail(error); }
  }
  async function write(action: string, args: string[], next: string) {
    if (!wallet) return fail("Connect a wallet before submitting a consensus write.");
    try { setStatus("working"); const hash = await writeGate(wallet, action, args); setStatus("accepted"); setMessage(`${action} accepted on Studionet: ${hash}`); if (action === "register_policy") setPolicyId(next); if (action === "assess_change") setAssessmentId(next); } catch (error) { fail(error); }
  }
  return <main>
    <header><div><span className="mark">PG</span><span className="eyebrow">GenLayer project</span></div><button className="wallet" onClick={connect}>{wallet ? `${wallet.slice(0, 6)}...${wallet.slice(-4)}` : "Connect wallet"}</button></header>
    <section className="intro"><p className="eyebrow">Challengeable change authorization</p><h1>PolicyChangeGate</h1><p>Put consequential policy changes through a durable, consensus-backed review lifecycle before they become the new baseline.</p><div className="links"><a href={explorer} target="_blank">Studio contract</a><a href={github} target="_blank">Source code</a></div></section>
    <section className="status" data-state={status}><strong>{status === "working" ? "Working" : status === "accepted" ? "Accepted" : status === "error" ? "Needs attention" : "Ready"}</strong><span>{message}</span></section>
    <section className="workspace">
      <div className="panel"><div className="panel-title"><span>01</span><h2>Register baseline</h2></div><label>Canonical policy URL<input value={policyUrl} onChange={(e) => setPolicyUrl(e.target.value)} /></label><label>Governance rules<textarea value={rules} onChange={(e) => setRules(e.target.value)} /></label><button onClick={() => write("register_policy", [policyUrl, rules], "policy-1")}>Register policy</button><div className="divider" /><label>Policy ID<input value={policyId} onChange={(e) => setPolicyId(e.target.value)} /></label><button className="secondary" onClick={() => read("policy")}>Read on-chain policy</button></div>
      <div className="panel"><div className="panel-title"><span>02</span><h2>Assess candidate</h2></div><label>Candidate policy URL<input value={candidateUrl} onChange={(e) => setCandidateUrl(e.target.value)} /></label><button onClick={() => write("assess_change", [policyId, candidateUrl], "assessment-1")}>Request consensus assessment</button><div className="divider" /><div className="panel-title"><span>03</span><h2>Challenge or resolve</h2></div><label>Assessment ID<input value={assessmentId} onChange={(e) => setAssessmentId(e.target.value)} placeholder="assessment-1" /></label><label>Independent challenge evidence<input value={challengeUrl} onChange={(e) => setChallengeUrl(e.target.value)} /></label><div className="actions"><button className="secondary" onClick={() => write("challenge_change", [assessmentId, challengeUrl], "")}>Challenge</button><button className="secondary" onClick={() => write("resolve_challenge", [assessmentId], "")}>Resolve</button></div><div className="actions"><button className="secondary" onClick={() => write("finalize_change", [assessmentId], "")}>Finalize approved change</button><button className="secondary" onClick={() => read("assessment")}>Read assessment</button></div></div>
      <aside className="record"><div className="panel-title"><span>Ledger</span><h2>Contract record</h2></div><p>Reads always render the exact contract response. This interface does not calculate a local verdict.</p><pre>{record || "No record loaded yet."}</pre><ul><li>Owner-only baseline and finalization</li><li>Open challenge with independent evidence</li><li>Persistent policy and assessment IDs</li><li>Stable URL commitments, not dynamic HTML equality</li></ul></aside>
    </section>
  </main>;
}
