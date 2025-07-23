'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui'
import { NewProjectModal } from '@/components/modals/NewProjectModal'
import {
  LayoutDashboard,
  FolderOpen,
  Settings,
  PlayCircle,
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
        'bg-white dark:bg-neutral-900 border-r border-neutral-200 dark:border-neutral-800 transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-64',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-800">
        {!isCollapsed && (
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 flex items-center justify-center">
              <Image 
                src="/ekona_logo_transparent.png" 
                alt="Ekona Logo" 
                width={40} 
                height={40}
                className="object-contain"
              />
            </div>
            <div>
              <h2 className="text-lg font-light text-neutral-900 dark:text-white">
                Ekona
              </h2>
              <p className="text-xs text-neutral-600 dark:text-neutral-400 font-light">
                Slide Creator
              </p>
            </div>
          </div>
        )}
        {isCollapsed && (
          <div className="w-8 h-8 flex items-center justify-center">
            <Image 
              src="/ekona_logo_transparent.png" 
              alt="Ekona Logo" 
              width={32} 
              height={32}
              className="object-contain"
            />
          </div>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4 text-neutral-500" />
          ) : (
            <ChevronLeft className="w-4 h-4 text-neutral-500" />
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
              'w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors font-light',
              'bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm',
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
                  'flex items-center gap-3 px-3 py-2 rounded-md transition-colors group font-light',
                  isActive
                    ? 'bg-primary/10 dark:bg-primary/20 text-primary dark:text-primary'
                    : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800',
                  isCollapsed && 'justify-center'
                )}
              >
                <Icon className={cn(
                  'w-4 h-4 flex-shrink-0',
                  isActive ? 'text-primary dark:text-primary' : 'text-neutral-500 dark:text-neutral-400'
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
                  <div className="absolute left-full ml-2 px-2 py-1 bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900 text-xs rounded-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                    {item.title}
                    {item.description && (
                      <div className="text-neutral-300 dark:text-neutral-600">
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
            <h3 className="px-3 text-xs font-light text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">
              Recent Projects
            </h3>
            <div className="space-y-1">
              {/* Placeholder for recent projects - will be populated dynamically */}
              <div className="px-3 py-2 text-sm text-neutral-500 dark:text-neutral-400 italic font-light">
                No recent projects
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* Footer */}
      {!isCollapsed && (
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-neutral-200 dark:border-neutral-800">
          <div className="text-xs text-neutral-500 dark:text-neutral-400 text-center font-light">
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