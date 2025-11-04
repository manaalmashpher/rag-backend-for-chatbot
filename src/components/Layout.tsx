import React, { useState, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  FileText,
  Upload,
  Search,
  BarChart3,
  LogOut,
  ChevronDown,
  Building2,
  MessageCircle,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(event.target as Node)
      ) {
        setShowUserMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const navigation = [
    { name: "Home", href: "/", icon: FileText },
    { name: "Upload", href: "/upload", icon: Upload },
    { name: "Status", href: "/status", icon: BarChart3 },
    { name: "Search", href: "/search", icon: Search },
    { name: "Chat", href: "/chat", icon: MessageCircle },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="container">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900">IonologyBot</h1>
            </div>

            <div className="flex items-center space-x-4">
              {/* Desktop Navigation */}
              <nav className="hidden md:flex space-x-8">
                {navigation.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.href;
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline hover:no-underline ${
                        isActive
                          ? "bg-blue-100 text-blue-700"
                          : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                      }`}
                      style={{ textDecoration: "none" }}
                    >
                      <Icon size={16} />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </nav>

              {/* User Menu */}
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className={`flex items-center space-x-3 px-4 py-2 rounded-lg transition-all duration-200 focus:outline-none border-0 outline-none ring-0 ${
                    showUserMenu
                      ? "text-blue-700 hover:bg-gray-50"
                      : "text-blue-700 hover:bg-gray-50"
                  }`}
                  style={{ border: "none", outline: "none" }}
                >
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-sm font-semibold">
                    {user?.email?.charAt(0).toUpperCase()}
                  </div>
                  <span className="hidden md:block font-medium">
                    {user?.email}
                  </span>
                  <ChevronDown
                    size={16}
                    className={`transition-transform duration-200 ${
                      showUserMenu ? "rotate-180" : ""
                    }`}
                  />
                </button>

                {showUserMenu && (
                  <div
                    className="absolute right-0 mt-3 bg-white rounded-xl shadow-xl border border-gray-200 py-3 px-3 z-50 animate-in slide-in-from-top-2 duration-200"
                    style={{
                      width: "220px",
                      minWidth: "220px",
                      maxWidth: "220px",
                    }}
                  >
                    <div className="flex items-start space-x-3 pt-2">
                      <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0 px-3 pt-6 pb-4">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-lg font-semibold">
                          {user?.email?.charAt(0).toUpperCase()}
                        </div>
                      </div>
                      <div className="pt-5 pl-3 pr-6 py-4 flex-1">
                        <div className="font-semibold text-gray-900 text-base mb-2 pt-2">
                          {user?.email}
                        </div>
                        <div className="text-sm text-gray-500 flex items-center whitespace-nowrap">
                          <Building2 size={14} className="mr-2 flex-shrink-0" />
                          <span>Organization ID: {user?.organization_id}</span>
                        </div>
                      </div>
                    </div>
                    <div className="py-2">
                      <button
                        onClick={handleLogout}
                        className="flex items-center space-x-2 px-5 py-2 text-sm text-gray-700 hover:bg-red-50 hover:text-red-700 transition-colors duration-200 group rounded-md border-0 outline-none mx-4"
                        style={{
                          border: "none",
                          outline: "none",
                          borderRadius: "6px",
                          paddingLeft: "16px",
                          paddingRight: "16px",
                        }}
                      >
                        <LogOut
                          size={18}
                          className="group-hover:text-red-600"
                        />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Mobile menu button */}
              <div className="md:hidden">
                <button
                  type="button"
                  className="p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                  aria-label="Open menu"
                >
                  <svg
                    className="h-6 w-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 6h16M4 12h16M4 18h16"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden border-t border-gray-200">
          <div className="px-2 pt-2 pb-3 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-base font-medium transition-colors ${
                    isActive
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                  }`}
                >
                  <Icon size={16} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-8">{children}</main>
    </div>
  );
};

export default Layout;
