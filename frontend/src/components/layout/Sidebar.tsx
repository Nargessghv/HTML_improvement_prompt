'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button, Badge } from '@/components/ui'
import { 
  Tooltip, 
  TooltipContent, 
  TooltipProvider, 
  TooltipTrigger 
} from '@/components/ui/tooltip'
import { NewProjectModal } from '@/components/modals/NewProjectModal'
import {
  LayoutDashboard,
  FolderOpen,
  Settings,
  PlayCircle,
  Plus,
  ChevronLeft,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen
} from 'lucide-react'

interface SidebarProps {
  className?: string
}

interface NavItem {
  title: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string
  description?: string
}

const navigation: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
    description: 'Overview and recent activity'
  },
  {
    title: 'Projects',
    href: '/projects',
    icon: FolderOpen,
    description: 'Manage your presentations'
  },
  {
    title: 'Workflow',
    href: '/workflow',
    icon: PlayCircle,
    description: 'Monitor generation progress'
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'Account and preferences'
  }
]

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [showNewProjectModal, setShowNewProjectModal] = useState(false)

  return (
    <TooltipProvider>
      <aside 
        className={cn(
          'bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 h-full flex flex-col relative',
          isCollapsed ? 'w-16' : 'w-64',
          className
        )}
      >
        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4">
          {/* Collapse Toggle */}
          <div className="px-3 mb-6 flex justify-end">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsCollapsed(!isCollapsed)}
                  className="h-8 w-8 p-0 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  {isCollapsed ? (
                    <PanelLeftOpen className="h-4 w-4" />
                  ) : (
                    <PanelLeftClose className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">
                {isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              </TooltipContent>
            </Tooltip>
          </div>

          {/* Quick Action */}
          <div className="px-3 mb-6">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={() => setShowNewProjectModal(true)}
                  className={cn(
                    'w-full bg-red-600 hover:bg-red-700 text-white shadow-lg hover:shadow-xl transition-all duration-300',
                    isCollapsed ? 'px-0' : 'justify-start'
                  )}
                >
                  <Plus className="h-4 w-4" />
                  {!isCollapsed && <span className="ml-2 font-medium">New Project</span>}
                </Button>
              </TooltipTrigger>
              {isCollapsed && (
                <TooltipContent side="right">
                  New Project
                </TooltipContent>
              )}
            </Tooltip>
          </div>

          {/* Main Navigation */}
          <div className="px-3 space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
              const Icon = item.icon

              return (
                <Tooltip key={item.href}>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      asChild
                      className={cn(
                        'w-full transition-all duration-200 hover:bg-gray-100 dark:hover:bg-gray-800',
                        isActive 
                          ? 'bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800/30' 
                          : 'text-gray-700 dark:text-gray-300',
                        isCollapsed ? 'px-0' : 'justify-start'
                      )}
                    >
                      <Link href={item.href}>
                        <Icon className={cn(
                          'h-4 w-4',
                          isActive ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-gray-400'
                        )} />
                        {!isCollapsed && (
                          <>
                            <span className="ml-3 font-medium">{item.title}</span>
                            {item.badge && (
                              <Badge variant="secondary" className="ml-auto text-xs">
                                {item.badge}
                              </Badge>
                            )}
                          </>
                        )}
                      </Link>
                    </Button>
                  </TooltipTrigger>
                  {isCollapsed && (
                    <TooltipContent side="right">
                      <div>
                        <div className="font-medium">{item.title}</div>
                        {item.description && (
                          <div className="text-xs text-gray-400 mt-1">{item.description}</div>
                        )}
                      </div>
                    </TooltipContent>
                  )}
                </Tooltip>
              )
            })}
          </div>

          {/* Recent Projects Section */}
          {!isCollapsed && (
            <div className="px-3 mt-8">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Recent Projects
                </h3>
              </div>
              <div className="space-y-1">
                <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400 italic">
                  No recent projects
                </div>
              </div>
            </div>
          )}
        </nav>

        {/* New Project Modal */}
        <NewProjectModal 
          open={showNewProjectModal}
          onOpenChange={setShowNewProjectModal}
        />
      </aside>
    </TooltipProvider>
  )
}