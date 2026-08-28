"use client";

import { useState } from "react";
import { POLICY_CHANGE_GATE_ADDRESS, readAssessment, readLatestAssessmentId, readLatestPolicyId, readPolicy, writeGate, type WalletAddress } from "@/lib/genlayer";

declare global { interface Window { ethereum?: { request(args: { method: string }): Promise<unknown> } } }
type Status = "ready" | "working" | "accepted" | "error";
const explorer = `https://explorer-studio.genlayer.com/address/${POLICY_CHANGE_GATE_ADDRESS}`;
const github = "https://github.com/klopp78/policychangegate-genlayer";
const asText = (value: unknown) => typeof value === "string" ? value : JSON.stringify(value, null, 2);

export default function Home() {
  const [wallet, setWallet] = useState<WalletAddress | null>(null);
  const [status, setStatus] = useState<Status>("ready");
  const [message, setMessage] = useState("Connect a Studio wallet to create challengeable policy-change records.");
  const [policyUrl, setPolicyUrl] = useState("https://docs.genlayer.com");
  const [rules, setRules] = useState("Owner may finalize only after a 24-hour challenge window; challenges require independent evidence.");
  const [policyId, setPolicyId] = useState("");
  const [candidateUrl, setCandidateUrl] = useState("https://docs.genlayer.com/developers");
  const [assessmentId, setAssessmentId] = useState("");
  const [challengeUrl, setChallengeUrl] = useState("https://docs.genlayer.com/developers/intelligent-contracts");
  const [record, setRecord] = useState("");
  const fail = (error: unknown) => { setStatus("error"); setMessage(error instanceof Error ? error.message : "The contract call did not complete."); };
  const load = async (kind: "policy" | "assessment", id: string) => {
    const value = kind === "policy" ? await readPolicy(id, wallet ?? undefined) : await readAssessment(id, wallet ?? undefined);
    setRecord(asText(value));
  };
  async function connect() {
    if (!window.ethereum) return fail("No browser wallet was detected.");
    try { setStatus("working"); const accounts = await window.ethereum.request({ method: "eth_requestAccounts" }) as string[]; if (!accounts[0]) throw new Error("Wallet did not return an account."); setWallet(accounts[0] as WalletAddress); setStatus("ready"); setMessage("Wallet connected. Contract reads and consensus writes are ready."); } catch (error) { fail(error); }
  }
  async function readRecord(kind: "policy" | "assessment") {
    const id = kind === "policy" ? policyId : assessmentId;
    if (!id) return fail(`Enter a ${kind} ID first.`);
    try { setStatus("working"); await load(kind, id); setStatus("ready"); setMessage(`${kind} ${id} loaded directly from contract storage.`); } catch (error) { fail(error); }
  }
  async function write(action: string, args: string[], generated: "policy" | "assessment" | null) {
    if (!wallet) return fail("Connect a wallet before submitting a consensus write.");
    try {
      setStatus("working");
      const { hash } = await writeGate(wallet, action, args);
      let generatedId = "";
      if (generated === "policy") { generatedId = String(await readLatestPolicyId(wallet)); setPolicyId(generatedId); await load("policy", generatedId); }
      if (generated === "assessment") { generatedId = String(await readLatestAssessmentId(wallet)); setAssessmentId(generatedId); await load("assessment", generatedId); }
      setStatus("accepted");
      setMessage(`${action} accepted on Studionet${generatedId ? `; generated ID: ${generatedId}` : ""}. Transaction: ${hash}`);
    } catch (error) { fail(error); }
  }
  return <main>
    <header><div><span className="mark">PG</span><span className="eyebrow">GenLayer project</span></div><button className="wallet" onClick={connect}>{wallet ? `${wallet.slice(0, 6)}...${wallet.slice(-4)}` : "Connect wallet"}</button></header>
    <section className="intro"><p className="eyebrow">Challengeable change authorization</p><h1>PolicyChangeGate</h1><p>Put consequential policy changes through a durable, consensus-backed lifecycle with a real challenge window before a new baseline can take effect.</p><div className="links"><a href={explorer} target="_blank">Studio contract</a><a href={github} target="_blank">Source code and tests</a></div></section>
    <section className="status" data-state={status}><strong>{status === "working" ? "Working" : status === "accepted" ? "Accepted" : status === "error" ? "Needs attention" : "Ready"}</strong><span>{message}</span></section>
    <section className="workspace">
      <div className="panel"><div className="panel-title"><span>01</span><h2>Register baseline</h2></div><label>Canonical policy URL<input value={policyUrl} onChange={(e) => setPolicyUrl(e.target.value)} /></label><label>Governance rules<textarea value={rules} onChange={(e) => setRules(e.target.value)} /></label><button onClick={() => write("register_policy", [policyUrl, rules], "policy")}>Register policy</button><div className="divider" /><label>Contract-generated policy ID<input value={policyId} onChange={(e) => setPolicyId(e.target.value)} placeholder="pol_1" /></label><button className="secondary" onClick={() => readRecord("policy")}>Read on-chain policy</button></div>
      <div className="panel"><div className="panel-title"><span>02</span><h2>Assess candidate</h2></div><label>Candidate policy URL<input value={candidateUrl} onChange={(e) => setCandidateUrl(e.target.value)} /></label><button onClick={() => write("assess_change", [policyId, candidateUrl], "assessment")}>Request consensus assessment</button><div className="divider" /><div className="panel-title"><span>03</span><h2>Challenge, resolve, retry</h2></div><label>Contract-generated change ID<input value={assessmentId} onChange={(e) => setAssessmentId(e.target.value)} placeholder="chg_1" /></label><label>Independent challenge evidence<input value={challengeUrl} onChange={(e) => setChallengeUrl(e.target.value)} /></label><div className="actions"><button className="secondary" onClick={() => write("challenge_change", [assessmentId, challengeUrl], null)}>Challenge</button><button className="secondary" onClick={() => write("resolve_challenge", [assessmentId], null)}>Resolve</button></div><div className="actions"><button className="secondary" onClick={() => write("retry_change", [assessmentId, candidateUrl], "assessment")}>Retry overturned change</button><button className="secondary" onClick={() => write("finalize_change", [assessmentId], null)}>Finalize after window</button></div><button className="secondary" onClick={() => readRecord("assessment")}>Read assessment</button></div>
      <aside className="record"><div className="panel-title"><span>Ledger</span><h2>Contract record</h2></div><p>Reads render the exact contract response. Generated IDs, challenge deadlines, source commitments, and retry ancestry come from on-chain state.</p><pre>{record || "No record loaded yet."}</pre><ul><li>24-hour immutable challenge window</li><li>Challenge uphold leads to finalize after window</li><li>Challenge overturn releases a policy for retry</li><li>URL and rendered-source commitments are persisted</li></ul></aside>
    </section>
  </main>;
}
