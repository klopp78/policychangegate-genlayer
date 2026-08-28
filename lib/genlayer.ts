import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

export const POLICY_CHANGE_GATE_ADDRESS = "0x229C614e7dD1A2B00df227f11402aB5dC1E1b828" as const;
export type WalletAddress = `0x${string}`;

function client(account?: WalletAddress) { return createClient({ chain: studionet, account }); }
function read(functionName: string, args: string[], account?: WalletAddress) {
  return client(account).readContract({ address: POLICY_CHANGE_GATE_ADDRESS, functionName, args, jsonSafeReturn: true });
}

export const readPolicy = (id: string, account?: WalletAddress) => read("get_policy", [id], account);
export const readAssessment = (id: string, account?: WalletAddress) => read("get_assessment", [id], account);
export const readLatestPolicyId = (account?: WalletAddress) => read("get_latest_policy_id", [], account);
export const readLatestAssessmentId = (account?: WalletAddress) => read("get_latest_assessment_id", [], account);

export async function writeGate(account: WalletAddress, functionName: string, args: string[]) {
  const sdk = client(account);
  await sdk.connect("studionet");
  const hash = await sdk.writeContract({ address: POLICY_CHANGE_GATE_ADDRESS, functionName, args, value: BigInt(0), leaderOnly: false });
  const receipt = await sdk.waitForTransactionReceipt({ hash, status: TransactionStatus.ACCEPTED });
  return { hash, receipt };
}
