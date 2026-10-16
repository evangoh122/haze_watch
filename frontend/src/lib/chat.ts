import { apiPost } from "./api";

export interface ChatSource {
  dataset_id?: string | null;
  source?: string | null;
  treatment?: string | null;
  license?: string | null;
}

export interface ChatResponse {
  reply: string;
  sources: ChatSource[];
  model: string;
  provider: string;
  fallback: boolean;
  guardrail_flags: string[];
  disclaimer: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

/** POST one chat turn to the backend chat layer. */
export function postChat(messages: ChatMessage[]): Promise<ChatResponse> {
  return apiPost<ChatResponse>("/chat", { messages });
}
