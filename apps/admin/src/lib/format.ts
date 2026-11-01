export function formatDate(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

/** Until staff accounts exist the server records a placeholder actor; show it as 관리자. */
export function actorLabel(actor?: string | null): string {
  if (!actor) return "-";
  return actor === "admin (no login yet)" ? "관리자" : actor;
}
