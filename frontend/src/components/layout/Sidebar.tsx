'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui'
import { NewProjectModal } from '@/components/modals/NewProjectModal'
import {
  LayoutDashboard,
  FolderOpen,
  Settings,
  PlayCircle,
  FileText,
  Plus,
  ChevronLeft,
  ChevronRight
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
    <aside 
      className={cn(
        'bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-64',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
        {!isCollapsed && (
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Ekona
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Slide Creator
              </p>
            </div>
          </div>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronLeft className="w-4 h-4 text-gray-500" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="p-2">
        {/* Quick Action */}
        <div className="mb-4">
          <button
            onClick={() => setShowNewProjectModal(true)}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors',
              'bg-blue-600 hover:bg-blue-700 text-white',
              isCollapsed && 'justify-center'
            )}
          >
            <Plus className="w-4 h-4" />
            {!isCollapsed && <span className="text-sm font-medium">New Project</span>}
          </button>
        </div>

        {/* Main Navigation */}
        <div className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
            const Icon = item.icon

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md transition-colors group',
                  isActive
                    ? 'bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800',
                  isCollapsed && 'justify-center'
                )}
              >
                <Icon className={cn(
                  'w-4 h-4 flex-shrink-0',
                  isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'
                )} />
                {!isCollapsed && (
                  <>
                    <span className="text-sm font-medium flex-1">{item.title}</span>
                    {item.badge && (
                      <Badge variant="secondary" className="text-xs">
                        {item.badge}
                      </Badge>
                    )}
                  </>
                )}
                
                {/* Tooltip for collapsed state */}
                {isCollapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs rounded-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                    {item.title}
                    {item.description && (
                      <div className="text-gray-300 dark:text-gray-600">
                        {item.description}
                      </div>
                    )}
                  </div>
                )}
              </Link>
            )
          })}
        </div>

        {/* Recent Projects Section */}
        {!isCollapsed && (
          <div className="mt-6">
            <h3 className="px-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
              Recent Projects
            </h3>
            <div className="space-y-1">
              {/* Placeholder for recent projects - will be populated dynamically */}
              <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400 italic">
                No recent projects
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* Footer */}
      {!isCollapsed && (
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-800">
          <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
            © 2024 Ekona Technologies
          </div>
        </div>
      )}
      
      {/* New Project Modal */}
      <NewProjectModal 
        open={showNewProjectModal}
        onOpenChange={setShowNewProjectModal}
      />
    </aside>
  )
}