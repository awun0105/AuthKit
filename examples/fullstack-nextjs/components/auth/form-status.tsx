export function FormStatus({
  error,
  success,
}: {
  error?: string | null;
  success?: string | null;
}) {
  if (error) {
    return (
      <p className="auth-error" role="alert">
        {error}
      </p>
    );
  }
  if (success) {
    return (
      <p className="auth-success" role="status">
        {success}
      </p>
    );
  }
  return null;
}
