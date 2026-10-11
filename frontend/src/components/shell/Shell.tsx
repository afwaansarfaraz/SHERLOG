import React, { useState } from "react"
import { Sidebar, type NavItemKey } from "./Sidebar"
import { Header } from "./Header"
import { SearchModal } from "./SearchModal"

interface ShellProps {
  children: ReactNode
  activeTab: NavItemKey
  onSelectTab: (tab: NavItemKey) => void
  onSelectIncident?: (id: string) => void
}

import type { ReactNode } from "react"

export const Shell: React.FC<ShellProps> = ({
  children,
  activeTab,
  onSelectTab,
  onSelectIncident,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const [isSearchOpen, setIsSearchOpen] = useState(false)

  return (
    <div className="h-screen bg-ink text-bone flex flex-row font-sans overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={onSelectTab}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed((prev) => !prev)}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <Header
          onOpenSearch={() => setIsSearchOpen(true)}
          onToggleMobileMenu={() => setIsMobileOpen(true)}
          onSelectIncident={onSelectIncident}
        />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto custom-scrollbar">{children}</main>
      </div>

      {/* Search Modal */}
      <SearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelectIncident={onSelectIncident}
      />
    </div>
  )
}
