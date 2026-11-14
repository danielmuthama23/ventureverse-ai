import type { Status } from "../lib/types";
export const StatusChip = ({ s }: { s: Status }) => <span className={`chip s-${s}`}>{s}</span>;
export const cap = (s: string) => s[0].toUpperCase() + s.slice(1);
