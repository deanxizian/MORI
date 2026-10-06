import spec from "./command_spec.json";
export const SPEC = spec;
export type CommandType = keyof typeof spec.commands;
export type Command = {
  protocol: string;
  device_id: string;
  session_id: string;
  command_id: string;
  client_id: string;
  source: string;
  permissions: string[];
  type: CommandType;
  params: Record<string, unknown>;
  sequence: number;
  sent_at_ms: number;
  basis_device_ms: number;
  valid_for_ms: number;
};
const keys = [
  "protocol",
  "device_id",
  "session_id",
  "command_id",
  "client_id",
  "source",
  "permissions",
  "type",
  "params",
  "sequence",
  "sent_at_ms",
  "basis_device_ms",
  "valid_for_ms",
].sort();
export function validate(c: unknown): Command {
  if (
    !c ||
    typeof c !== "object" ||
    Array.isArray(c) ||
    JSON.stringify(Object.keys(c).sort()) !== JSON.stringify(keys)
  )
    throw Error("ENVELOPE_FIELDS");
  const v = c as Command;
  if (v.protocol !== spec.protocol) throw Error("VERSION");
  for (const key of [
    "device_id",
    "session_id",
    "command_id",
    "client_id",
  ] as const)
    if (typeof v[key] !== "string" || !/^[a-zA-Z0-9_-]{1,64}$/.test(v[key]))
      throw Error("IDENTIFIER");
  if (!spec.sources.includes(v.source)) throw Error("SOURCE");
  if (
    !Array.isArray(v.permissions) ||
    !v.permissions.length ||
    v.permissions.length > spec.permissions.length ||
    new Set(v.permissions).size !== v.permissions.length ||
    v.permissions.some((p) => !spec.permissions.includes(p))
  )
    throw Error("PERMISSIONS");
  for (const [key, min, max] of [
    ["sequence", 1, 2147483647],
    ["sent_at_ms", 0, Number.MAX_SAFE_INTEGER],
    ["basis_device_ms", 0, Number.MAX_SAFE_INTEGER],
    ["valid_for_ms", 1, 30000],
  ] as const)
    if (!Number.isSafeInteger(v[key]) || v[key] < min || v[key] > max)
      throw Error("INTEGER_RANGE");
  const rule = spec.commands[v.type];
  if (!rule || v.valid_for_ms > rule.ttl_max_ms)
    throw Error("COMMAND_OR_EXPIRY");
  if (!v.permissions.includes(rule.permission))
    throw Error("PERMISSION_MISSING");
  if (
    !v.params ||
    typeof v.params !== "object" ||
    Array.isArray(v.params) ||
    JSON.stringify(Object.keys(v.params).sort()) !==
      JSON.stringify(Object.keys(rule.fields).sort())
  )
    throw Error("PARAM_FIELDS");
  for (const [key, r] of Object.entries(rule.fields) as [
    string,
    { kind: string; min: number; max: number; values?: readonly unknown[] },
  ][]) {
    const value = v.params[key];
    if (
      (r.kind === "number" || r.kind === "integer") &&
      (typeof value !== "number" ||
        !Number.isFinite(value) ||
        value < r.min ||
        value > r.max)
    )
      throw Error("NUMBER_RANGE");
    if (r.kind === "integer" && !Number.isInteger(value))
      throw Error("INTEGER_RANGE");
    if (r.kind === "boolean" && typeof value !== "boolean")
      throw Error("BOOLEAN");
    if (
      r.kind === "string" &&
      (typeof value !== "string" ||
        [...value].length > r.max ||
        value.includes("\0"))
    )
      throw Error("STRING");
    if (r.values && !r.values.includes(value)) throw Error("ENUM");
  }
  return v;
}
