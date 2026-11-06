"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity as ActivityIcon,
  CalendarDays,
  ChartNoAxesCombined,
  ClipboardList,
  Dumbbell,
  HeartPulse,
  LayoutDashboard,
  LogOut,
  Plus,
  Settings,
  Trophy,
} from "lucide-react";
import { api, type User } from "@/lib/api";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/activities", label: "Activities", icon: ActivityIcon },
  { href: "/strength", label: "Strength", icon: Dumbbell },
  { href: "/calendar", label: "Calendar", icon: CalendarDays },
  { href: "/training", label: "Training", icon: ClipboardList },
  { href: "/analytics", label: "Analytics", icon: ChartNoAxesCombined },
  { href: "/records", label: "Records", icon: Trophy },
  { href: "/health", label: "Health", icon: HeartPulse },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => router.replace("/login"))
      .finally(() => setReady(true));
  }, [router]);

  async function signOut() {
    await api<void>("/auth/logout", { method: "POST" }).catch(() => undefined);
    router.replace("/login");
  }

  if (!ready || !user)
    return <div className="loading">Loading your training space...</div>;

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link className="brand" href="/dashboard">
          <span className="brand-mark">
            <ActivityIcon size={17} strokeWidth={2.6} />
          </span>
          <span>
            <span className="brand-name">PACE</span>
            <span className="brand-sub" style={{ display: "block" }}>
              Training, with intention
            </span>
          </span>
        </Link>
        <div className="nav-label">Workspace</div>
        <nav className="nav-list" aria-label="Main navigation">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={`nav-link${active ? " active" : ""}`}
              >
                <Icon size={17} strokeWidth={1.8} />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <Link className="nav-link" href="/activities/new">
            <Plus size={17} />
            Log an activity
          </Link>
          <div className="profile-chip">
            <span className="avatar">
              {user.full_name.slice(0, 1).toUpperCase()}
            </span>
            <span>
              <span className="profile-name" style={{ display: "block" }}>
                {user.full_name}
              </span>
              <span className="profile-email" style={{ display: "block" }}>
                {user.email}
              </span>
            </span>
            <button
              className="signout"
              type="button"
              title="Sign out"
              aria-label="Sign out"
              onClick={signOut}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <span className="topbar-context">Your personal training log</span>
          <span className="topbar-date">
            {new Intl.DateTimeFormat("en", {
              weekday: "short",
              month: "short",
              day: "numeric",
            }).format(new Date())}
          </span>
        </header>
        {children}
      </main>
      <nav className="mobile-nav" aria-label="Mobile navigation">
        {links.slice(0, 4).map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`mobile-link${pathname.startsWith(href) ? " active" : ""}`}
          >
            <Icon size={19} />
            <span>{label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
