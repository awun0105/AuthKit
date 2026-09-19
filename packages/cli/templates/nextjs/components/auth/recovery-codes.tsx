export function RecoveryCodes({ codes }: { codes: string[] }) {
  if (codes.length === 0) return null;
  return (
    <div>
      <p>Store these backup codes. They are shown only once.</p>
      <ul>
        {codes.map((code) => (
          <li key={code}>
            <code>{code}</code>
          </li>
        ))}
      </ul>
    </div>
  );
}
