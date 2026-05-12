const THINK_RE = /<think>[\s\S]*?<\/think>/gi;

export function stripThinking(text: string): string {
  return text.replace(THINK_RE, '').trim();
}
