import React, { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";

interface RegisterFormProps {
  onSuccess?: () => void;
  onSwitchToLogin?: () => void;
}

export const RegisterForm: React.FC<RegisterFormProps> = ({
  onSuccess,
  onSwitchToLogin,
}) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const { register, error, clearError } = useAuth();

  const validatePasswords = () => {
    const errors: string[] = [];

    if (password !== confirmPassword) {
      errors.push("Passwords do not match");
    }

    if (password.length < 8) {
      errors.push("Password must be at least 8 characters long");
    }

    if (!/[A-Z]/.test(password)) {
      errors.push("Password must contain at least one uppercase letter");
    }

    if (!/[a-z]/.test(password)) {
      errors.push("Password must contain at least one lowercase letter");
    }

    if (!/\d/.test(password)) {
      errors.push("Password must contain at least one number");
    }

    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      errors.push("Password must contain at least one special character");
    }

    setValidationErrors(errors);
    return errors.length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    clearError();
    setValidationErrors([]);

    if (!validatePasswords()) {
      setIsSubmitting(false);
      return;
    }

    const success = await register(email, password, confirmPassword);
    if (success) {
      onSuccess?.();
    }
    setIsSubmitting(false);
  };

  return (
    <div className="w-full p-8 bg-white rounded-2xl shadow-xl border border-gray-100 transform transition-all duration-300 hover:shadow-2xl">
      <div className="text-center mb-8">
        <div className="mx-auto w-16 h-16 bg-gradient-to-br from-green-500 to-blue-600 rounded-full flex items-center justify-center mb-4">
          <svg
            className="w-8 h-8 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
            />
          </svg>
        </div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Create Account
        </h2>
        <p className="text-gray-600">Join us and get started today</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-400 rounded-r-lg">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {validationErrors.length > 0 && (
        <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-400 rounded-r-lg">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-red-800 mb-2">
                Please fix the following errors:
              </p>
              <ul className="text-sm text-red-700 space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index} className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>{error}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <label
            htmlFor="email"
            className="block text-sm font-semibold text-gray-700"
          >
            Email Address
          </label>
          <div className="relative">
            <div
              className="absolute inset-y-0 left-0 pl-7 flex items-center pointer-events-none"
              style={{
                marginLeft: "3px",
                display: "flex",
                alignItems: "center",
                height: "100%",
              }}
            >
              <svg
                className="h-5 w-5 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207"
                />
              </svg>
            </div>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 text-left"
              style={{ marginLeft: "-8px", width: "calc(100% + 16px)" }}
              placeholder="Enter your email"
            />
          </div>
        </div>

        <div className="space-y-2">
          <label
            htmlFor="password"
            className="block text-sm font-semibold text-gray-700"
          >
            Password
          </label>
          <div className="relative">
            <div
              className="absolute inset-y-0 left-0 pl-7 flex items-center pointer-events-none"
              style={{
                marginLeft: "3px",
                display: "flex",
                alignItems: "center",
                height: "100%",
              }}
            >
              <svg
                className="h-5 w-5 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
            </div>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 text-left"
              style={{ marginLeft: "-8px", width: "calc(100% + 16px)" }}
              placeholder="Create a strong password"
            />
          </div>
        </div>

        <div className="space-y-2">
          <label
            htmlFor="confirmPassword"
            className="block text-sm font-semibold text-gray-700"
          >
            Confirm Password
          </label>
          <div className="relative">
            <div
              className="absolute inset-y-0 left-0 pl-7 flex items-center pointer-events-none"
              style={{
                marginLeft: "3px",
                display: "flex",
                alignItems: "center",
                height: "100%",
              }}
            >
              <svg
                className="h-5 w-5 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 text-left"
              style={{ marginLeft: "-8px", width: "calc(100% + 16px)" }}
              placeholder="Confirm your password"
            />
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <h4 className="text-sm font-semibold text-blue-900 mb-2">
            Password Requirements:
          </h4>
          <ul className="text-xs text-blue-800 space-y-1">
            <li className="flex items-center">
              <span
                className={`mr-2 ${
                  password.length >= 8 ? "text-green-500" : "text-gray-400"
                }`}
              >
                {password.length >= 8 ? "✓" : "○"}
              </span>
              At least 8 characters
            </li>
            <li className="flex items-center">
              <span
                className={`mr-2 ${
                  /[A-Z]/.test(password) ? "text-green-500" : "text-gray-400"
                }`}
              >
                {/[A-Z]/.test(password) ? "✓" : "○"}
              </span>
              One uppercase letter
            </li>
            <li className="flex items-center">
              <span
                className={`mr-2 ${
                  /[a-z]/.test(password) ? "text-green-500" : "text-gray-400"
                }`}
              >
                {/[a-z]/.test(password) ? "✓" : "○"}
              </span>
              One lowercase letter
            </li>
            <li className="flex items-center">
              <span
                className={`mr-2 ${
                  /\d/.test(password) ? "text-green-500" : "text-gray-400"
                }`}
              >
                {/\d/.test(password) ? "✓" : "○"}
              </span>
              One number
            </li>
            <li className="flex items-center">
              <span
                className={`mr-2 ${
                  /[!@#$%^&*(),.?":{}|<>]/.test(password)
                    ? "text-green-500"
                    : "text-gray-400"
                }`}
              >
                {/[!@#$%^&*(),.?":{}|<>]/.test(password) ? "✓" : "○"}
              </span>
              One special character
            </li>
          </ul>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="mx-auto flex justify-center items-center py-4 px-12 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transform transition-all duration-200 hover:scale-105 active:scale-95"
          style={{ width: "120px", backgroundColor: "#60a5fa", color: "white" }}
        >
          {isSubmitting ? (
            <>
              <svg
                className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              Creating account...
            </>
          ) : (
            "Create Account"
          )}
        </button>
      </form>

      {onSwitchToLogin && (
        <div className="mt-8 text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{" "}
            <span
              onClick={onSwitchToLogin}
              className="font-semibold text-blue-600 hover:text-blue-500 cursor-pointer underline transition-colors duration-200"
            >
              Sign in here
            </span>
          </p>
        </div>
      )}
    </div>
  );
};
