export default function LoginPage() {
  return (
    <div className="login-page">
      <div className="login-card">
        <svg className="mark" viewBox="0 0 64 64" width="40" height="40">
          <circle cx="32" cy="32" r="28" stroke="#14130F" strokeWidth="3" fill="none" />
          <circle cx="32" cy="32" r="9" fill="#1F6B47" />
        </svg>
        <h1>apt.</h1>
        <p>Sign in to see your job digest</p>
        <a className="login-btn" href="/api/auth/login/google">
          Continue with Google
        </a>
      </div>
    </div>
  );
}
