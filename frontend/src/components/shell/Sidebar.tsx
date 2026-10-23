import React from "react"
import {
  LayoutDashboard,
  AlertTriangle,
  Server,
  BookOpen,
  FileCheck2,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
} from "lucide-react"
import { cn } from "../../lib/utils"

export type NavItemKey =
  "overview" | "incidents" | "services" | "knowledge" | "evaluations" | "audit-logs" | "settings"

interface SidebarProps {
  activeTab: NavItemKey
  onSelectTab: (tab: NavItemKey) => void
  activeIncidentsCount?: number
  isCollapsed?: boolean
  onToggleCollapse?: () => void
  isMobileOpen?: boolean
  onCloseMobile?: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  activeIncidentsCount = 3,
  isCollapsed = false,
  onToggleCollapse,
  isMobileOpen = false,
  onCloseMobile,
}) => {
  const navItems = [
    {
      key: "overview" as NavItemKey,
      label: "Overview",
      icon: LayoutDashboard,
    },
    {
      key: "incidents" as NavItemKey,
      label: "Incidents",
      icon: AlertTriangle,
      badge: activeIncidentsCount > 0 ? activeIncidentsCount : undefined,
      badgeVariant: "vermilion",
    },
    {
      key: "services" as NavItemKey,
      label: "Applications",
      icon: Server,
    },
    {
      key: "knowledge" as NavItemKey,
      label: "Knowledge",
      icon: BookOpen,
    },
    {
      key: "evaluations" as NavItemKey,
      label: "Evaluations",
      icon: FileCheck2,
    },
    {
      key: "audit-logs" as NavItemKey,
      label: "Audit Logs",
      icon: FileText,
    },
    {
      key: "settings" as NavItemKey,
      label: "Settings",
      icon: Settings,
    },
  ]

  const sidebarContent = (
    <div className="flex flex-col h-full bg-ink border-r border-ash select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-5 border-b border-ash shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-soot border border-ash flex items-center justify-center text-amber shrink-0">
            <Shield className="w-4 h-4" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="font-semibold text-bone text-sm tracking-widest font-sans uppercase">
                SHERLOG
              </span>
              <span className="text-[10px] text-dust font-mono tracking-wider uppercase -mt-0.5">
                AI Incident Investigation
              </span>
            </div>
          )}
        </div>
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            aria-label="Toggle sidebar collapse"
            className="hidden lg:flex w-6 h-6 items-center justify-center rounded text-dust hover:text-bone hover:bg-soot border border-transparent hover:border-ash transition-colors"
          >
            {isCollapsed ? (
              <ChevronRight className="w-3.5 h-3.5" />
            ) : (
              <ChevronLeft className="w-3.5 h-3.5" />
            )}
          </button>
        )}
      </div>

      {/* Nav List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeTab === item.key

          return (
            <button
              key={item.key}
              onClick={() => {
                onSelectTab(item.key)
                if (onCloseMobile) onCloseMobile()
              }}
              title={isCollapsed ? item.label : undefined}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-all group relative text-left",
                isActive
                  ? "bg-soot text-bone border border-ash/80 shadow-sm"
                  : "text-dust hover:text-bone hover:bg-soot/50 border border-transparent"
              )}
            >
              <Icon
                className={cn(
                  "w-4 h-4 shrink-0 transition-colors",
                  isActive ? "text-bone" : "text-dust group-hover:text-bone"
                )}
              />
              {!isCollapsed && <span className="flex-1 truncate tracking-wide">{item.label}</span>}
              {!isCollapsed && item.badge !== undefined && (
                <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-[#3A1E18] text-vermilion border border-[#5E271D]">
                  {item.badge}
                </span>
              )}
              {isCollapsed && item.badge !== undefined && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-vermilion ring-2 ring-ink" />
              )}
            </button>
          )
        })}
      </nav>

      {/* Footer System Meta */}
      {!isCollapsed && (
        <div className="p-3 border-t border-ash/70 shrink-0">
          <div className="bg-soot/60 border border-ash/60 rounded px-3 py-2 text-[11px] font-mono text-dust flex items-center justify-between">
            <span className="truncate">SRE Agent v1.0</span>
            <span className="text-verdigris flex items-center gap-1 shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-verdigris animate-pulse" />
              READY
            </span>
          </div>
        </div>
      )}
    </div>
  )

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={cn(
          "hidden md:block shrink-0 h-screen sticky top-0 transition-all duration-200 z-30",
          isCollapsed ? "w-16" : "w-60"
        )}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Overlay */}
      {isMobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-ink/80 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobile}
          />
          <div className="relative w-64 max-w-[80%] h-full z-10 shadow-xl">{sidebarContent}</div>
        </div>
      )}
    </>
  )
}
