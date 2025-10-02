import React from "react";
import { useAuth } from "../../contexts/AuthContext";

interface AuthGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  requireAuth?: boolean;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({
  children,
  fallback = null,
  requireAuth = true,
}) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (requireAuth && !isAuthenticated) {
    return <>{fallback}</>;
  }

  if (!requireAuth && isAuthenticated) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};
