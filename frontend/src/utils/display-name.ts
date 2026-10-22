/** First whitespace-separated token of a full name, capitalized, for greeting copy only — never
 * sent to the backend or used to identify a learner. Only the first letter is touched (e.g.
 * "yass" → "Yass"); the rest of the token is left exactly as typed, so this never fights a name
 * with its own internal capitalization (e.g. "McKay"). Falls through unchanged for an empty
 * input. */
export function firstNameOf(fullName: string): string {
  const trimmed = fullName.trim();
  if (!trimmed) return trimmed;
  const first = trimmed.split(/\s+/)[0];
  return first.charAt(0).toUpperCase() + first.slice(1);
}
