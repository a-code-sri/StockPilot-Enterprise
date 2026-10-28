import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { MOCK_MODE } from "../config";

export default function Register() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleRegister = async (e) => {
    e.preventDefault();

    if (MOCK_MODE) {
      alert("Mock user registered successfully!");
      navigate("/");
      return;
    }

    try {
      await api.post("/auth/register", {
        email,
        username,
        password,
      });
      alert("User registered successfully!");
      navigate("/");
    } catch {
      alert("Registration failed");
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-indigo-900 to-black text-white">
      <form
        onSubmit={handleRegister}
        className="bg-white/10 backdrop-blur-xl p-8 rounded-xl w-96"
      >
        <h2 className="text-2xl font-bold mb-6 text-center">Create Account</h2>

        <input
          className="w-full p-3 mb-3 rounded bg-white/20"
          placeholder="Email"
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          className="w-full p-3 mb-3 rounded bg-white/20"
          placeholder="Username"
          onChange={(e) => setUsername(e.target.value)}
        />

        <input
          type="password"
          className="w-full p-3 mb-4 rounded bg-white/20"
          placeholder="Password"
          onChange={(e) => setPassword(e.target.value)}
        />

        <button
          type="submit"
          className="w-full bg-indigo-600 py-2 rounded"
        >
          Register
        </button>
      </form>
    </div>
  );
}