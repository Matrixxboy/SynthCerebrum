import React from "react";

export default function JsonRenderer({ data }: { data: any }) {
  if (!data) return null;
  if (data.type === "table" && Array.isArray(data.rows)) {
    const cols = Array.from(
      new Set(data.rows.flatMap((r: any) => Object.keys(r))),
    );
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr>
              {cols.map((c) => (
                <th
                  key={c}
                  className="text-left font-medium p-2 border-b bg-muted/50"
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row: any, idx: number) => (
              <tr key={idx} className="odd:bg-muted/20">
                {cols.map((c) => (
                  <td key={c} className="p-2 align-top">
                    {String(row[c] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  if (data.type === "list" && Array.isArray(data.items)) {
    return (
      <ul className="text-xs list-disc pl-5">
        {data.items.map((it: any, i: number) => (
          <li key={i}>
            {it.source} — {it.score}%
          </li>
        ))}
      </ul>
    );
  }
  return (
    <pre className="text-xs overflow-auto">{JSON.stringify(data, null, 2)}</pre>
  );
}
