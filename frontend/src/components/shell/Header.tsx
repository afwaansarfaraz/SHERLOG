import React, { useState } from "react"
import { Search, Bell, RefreshCw, Menu, ChevronDown, User, ShieldAlert, LogOut, Sparkles } from "lucide-react"
import { NotificationsPopover } from "./NotificationsPopover"

interface HeaderProps {
  onOpenSearch: () => void
  onToggleMobileMenu: () => void
  onSelectIncident?: (id: string) => void
}

export const Header: React.FC<HeaderProps> = ({
  onOpenSearch,
  onToggleMobileMenu,
  onSelectIncident,
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)

  const handleRefresh = () => {
    setIsRefreshing(true)
    setTimeout(() => setIsRefreshing(false), 800)
  }

  return (
    <header className="h-16 shrink-0 bg-ink border-b border-ash px-4 sm:px-6 flex items-center justify-between gap-4 sticky top-0 z-20 select-none">
      {/* Left Area: Mobile Menu & Search Input */}
      <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0 max-w-xl">
        <button
          onClick={onToggleMobileMenu}
          aria-label="Open mobile navigation"
          className="md:hidden p-2 text-dust hover:text-bone hover:bg-soot rounded-md border border-transparent hover:border-ash transition-colors shrink-0"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Search Bar Button */}
        <button
          onClick={onOpenSearch}
          className="w-full flex items-center justify-between gap-2 px-3 py-1.5 rounded-md bg-soot/80 border border-ash/90 hover:border-[#4A4237] text-dust hover:text-bone text-xs transition-colors group cursor-pointer text-left min-w-0"
        >
          <div className="flex items-center gap-2 truncate min-w-0 flex-1">
            <Search className="w-4 h-4 text-dust group-hover:text-bone transition-colors shrink-0" />
            <span className="truncate">Search incidents, services, logs...</span>
          </div>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono text-dust bg-ink border border-ash/80 rounded shrink-0">
            <span>⌘</span>
            <span>K</span>
          </kbd>
        </button>
      </div>

      {/* Right Area: System Status, Actions & User */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* System Status Pill */}
        <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-full bg-soot/60 border border-ash text-xs text-bone font-mono">
          <span className="w-2 h-2 rounded-full bg-verdigris animate-pulse shrink-0" />
          <span className="text-[11px] text-dust">System Operational</span>
        </div>

        {/* Refresh Action */}
        <button
          onClick={handleRefresh}
          title="Refresh telemetry"
          className="p-1.5 rounded-md text-dust hover:text-bone hover:bg-soot border border-transparent hover:border-ash transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-bone" : ""}`} />
        </button>

        {/* Notifications Popover */}
        <div className="relative">
          <button
            onClick={() => setIsNotificationsOpen((prev) => !prev)}
            aria-label="Notifications"
            className="p-1.5 rounded-md text-dust hover:text-bone hover:bg-soot border border-transparent hover:border-ash transition-colors relative"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-vermilion ring-2 ring-ink" />
          </button>
          <NotificationsPopover
            isOpen={isNotificationsOpen}
            onClose={() => setIsNotificationsOpen(false)}
            onSelectIncident={onSelectIncident}
          />
        </div>

        {/* Divider */}
        <div className="h-5 w-px bg-ash" />

        {/* User Profile */}
        <div className="relative">
          <button
            onClick={() => setIsUserMenuOpen((prev) => !prev)}
            className="flex items-center gap-2.5 p-1 rounded-md hover:bg-soot border border-transparent hover:border-ash transition-colors text-left"
          >
            <div className="w-7 h-7 rounded-full bg-[#27211B] border border-ash flex items-center justify-center font-mono text-xs font-semibold text-bone shrink-0">
              AF
            </div>
            <div className="hidden lg:flex flex-col">
              <span className="text-xs font-medium text-bone leading-tight">Afwaan</span>
              <span className="text-[10px] text-dust font-mono leading-tight">admin</span>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-dust hidden lg:block" />
          </button>

          {/* User Dropdown */}
          {isUserMenuOpen && (
            <div
              className="absolute right-0 top-12 w-48 bg-soot border border-ash rounded-lg shadow-xl py-1 z-50 animate-in fade-in duration-100 text-xs"
              onMouseLeave={() => setIsUserMenuOpen(false)}
            >
              <div className="px-3 py-2 border-b border-ash/70">
                <p className="font-medium text-bone">Afwaan</p>
                <p className="text-[10px] font-mono text-dust">afwaan@sherlog.internal</p>
              </div>
              <button
                onClick={() => setIsUserMenuOpen(false)}
                className="w-full flex items-center gap-2 px-3 py-2 text-dust hover:text-bone hover:bg-ink/60 transition-colors text-left"
              >
                <User className="w-3.5 h-3.5" /> Profile Settings
              </button>
              <button
                onClick={() => setIsUserMenuOpen(false)}
                className="w-full flex items-center gap-2 px-3 py-2 text-dust hover:text-bone hover:bg-ink/60 transition-colors text-left"
              >
                <ShieldAlert className="w-3.5 h-3.5 text-amber" /> RBAC Permissions
              </button>
              {import.meta.env.DEV && (
                <button
                  onClick={() => {
                    setIsUserMenuOpen(false)
                    window.location.hash = "dev/hardening"
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-amber hover:text-bone hover:bg-ink/60 transition-colors text-left font-mono text-[11px]"
                >
                  <Sparkles className="w-3.5 h-3.5" /> Dev Hardening Showcase
                </button>
              )}
              <div className="border-t border-ash/70 my-1" />
              <button
                onClick={() => setIsUserMenuOpen(false)}
                className="w-full flex items-center gap-2 px-3 py-2 text-oxblood hover:bg-[#2B1417] transition-colors text-left"
              >
                <LogOut className="w-3.5 h-3.5" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
