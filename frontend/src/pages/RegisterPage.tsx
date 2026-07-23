import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest, setToken } from "../lib/api";

export function RegisterPage() {
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [invitationCode, setInvitationCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await apiRequest<{ access_token: string }>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, display_name: displayName, invitation_code: invitationCode })
      });
      setToken(result.access_token);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <form className="auth-panel" onSubmit={handleSubmit}>
        <h1>注册</h1>
        <label>
          昵称
          <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required />
        </label>
        <label>
          邮箱
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <label>
          密码
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} />
        </label>
        <label>
          邀请码
          <input value={invitationCode} onChange={(event) => setInvitationCode(event.target.value)} required />
        </label>
        {error ? <div className="error-text">{error}</div> : null}
        <button className="button primary" type="submit" disabled={loading}>
          {loading ? "创建中..." : "创建账号"}
        </button>
        <p>
          已有账号？<Link to="/login">登录</Link>
        </p>
      </form>
    </main>
  );
}
