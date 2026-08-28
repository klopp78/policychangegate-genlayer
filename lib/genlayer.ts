import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

export const POLICY_CHANGE_GATE_ADDRESS = "0x229C614e7dD1A2B00df227f11402aB5dC1E1b828" as const;
export type WalletAddress = `0x${string}`;

function client(account?: WalletAddress) { return createClient({ chain: studionet, account }); }

export async function readPolicy(policyId: string, account?: WalletAddress) {
  return client(account).readContract({ address: POLICY_CHANGE_GATE_ADDRESS, functionName: "get_policy", args: [policyId], jsonSafeReturn: true });
}

export async function readAssessment(assessmentId: string, account?: WalletAddress) {
  return client(account).readContract({ address: POLICY_CHANGE_GATE_ADDRESS, functionName: "get_assessment", args: [assessmentId], jsonSafeReturn: true });
}

export async function writeGate(account: WalletAddress, functionName: string, args: string[]) {
  const sdk = client(account);
  await sdk.connect("studionet");
  const hash = await sdk.writeContract({ address: POLICY_CHANGE_GATE_ADDRESS, functionName, args, value: BigInt(0), leaderOnly: false });
  await sdk.waitForTransactionReceipt({ hash, status: TransactionStatus.ACCEPTED });
  return hash;
}
