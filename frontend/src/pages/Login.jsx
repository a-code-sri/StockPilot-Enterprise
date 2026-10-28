import { useState, useContext } from "react";
import { AuthContext } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import { MOCK_MODE } from "../config";

export default function Login() {
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async () => {
    const success = await login(username, password);
    if (success) navigate("/dashboard");
    else alert("Login failed");
  };

  return (
    <div className="relative flex items-center justify-center min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-black overflow-hidden">

      <div className="absolute w-96 h-96 bg-purple-500 rounded-full blur-3xl opacity-30 -top-20 -left-20"></div>
      <div className="absolute w-96 h-96 bg-indigo-500 rounded-full blur-3xl opacity-30 bottom-0 right-0"></div>

      <div className="relative backdrop-blur-xl bg-white/10 border border-white/20 p-10 rounded-2xl shadow-2xl w-[400px] text-white">

        <h1 className="text-3xl font-bold mb-2 text-center">
          Business OS
        </h1>
        <p className="text-center text-gray-300 mb-8">
          Smart Manufacturing Control Panel
        </p>

        <input
          className="w-full p-3 mb-4 rounded-lg bg-white/20 border border-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-400 placeholder-gray-300"
          placeholder="Username"
          onChange={(e) => setUsername(e.target.value)}
        />

        <input
          type="password"
          className="w-full p-3 mb-6 rounded-lg bg-white/20 border border-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-400 placeholder-gray-300"
          placeholder="Password"
          onChange={(e) => setPassword(e.target.value)}
        />

        <button
          onClick={handleSubmit}
          className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-90 transition duration-300 py-3 rounded-lg font-semibold shadow-lg"
        >
          {MOCK_MODE ? "Login (Mock Mode)" : "Login"}
        </button>

        <button
          onClick={() => navigate("/register")}
          className="w-full mt-3 border border-white/30 hover:bg-white/10 transition duration-300 py-3 rounded-lg font-semibold"
        >
          Sign Up / Register
        </button>

        {MOCK_MODE && (
          <p className="text-xs text-center text-yellow-300 mt-6">
            Mock Mode Enabled
          </p>
        )}
      </div>
    </div>
  );
}
