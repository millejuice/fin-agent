import React from 'react'

export default function AnomalyBadge({ flag }: { flag: boolean }): React.ReactElement | null {
  if (!flag) return null;
  return (
    <span style={{
      background: "#fee2e2", color: "#b91c1c",
      padding: "2px 8px", borderRadius: 999, fontSize: 12, marginLeft: 8
    }}>
      이상 신호
    </span>
  );
}
