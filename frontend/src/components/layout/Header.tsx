'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui'
import {
  Search,
  Bell,
  Menu,
  Settings,
  User,
  LogOut,
  HelpCircle,
  Moon,
  Sun
} from 'lucide-react'
import { Sidebar } from './Sidebar'

interface HeaderProps {
  className?: string
}

export function Header({ className }: HeaderProps) {
  const { user, signOut } = useSupabaseAuth()
  const [isDarkMode, setIsDarkMode] = useState(false)

  const handleSignOut = async () => {
    await signOut()
  }

  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode)
    // TODO: Implement dark mode toggle logic
  }

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  const userName = user?.user_metadata?.full_name || user?.email || 'User'
  const userEmail = user?.email || ''

  return (
    <header className={`bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 ${className}`}>
      <div className="flex items-center justify-between h-16 px-4 lg:px-6">
        {/* Logo and Mobile Menu */}
        <div className="flex items-center space-x-4">
          {/* Mobile Menu */}
          <div className="lg:hidden">
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-64 p-0">
                <SheetHeader className="sr-only">
                  <SheetTitle>Navigation</SheetTitle>
                </SheetHeader>
                <Sidebar />
              </SheetContent>
            </Sheet>
          </div>
          
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 lg:w-12 lg:h-12 flex items-center justify-center">
              <Image 
                src="/ekona_logo_transparent.png" 
                alt="Ekona Logo" 
                width={48} 
                height={48}
                className="object-contain group-hover:scale-105 transition-transform duration-200"
              />
            </div>
            <div className="hidden sm:block">
              <div className="h-8 w-px bg-gray-300 dark:bg-gray-600 mx-3"></div>
            </div>
            <div className="hidden sm:block">
              <p className="text-sm lg:text-base font-light text-gray-700 dark:text-gray-300 tracking-wide">
                CONTENT CREATION HUB
              </p>
            </div>
          </Link>
        </div>

        {/* Search Bar */}
        <div className="flex-1 max-w-lg mx-6 lg:mx-8">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search projects, slides..."
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-red-500 focus:border-transparent shadow-sm hover:shadow-md transition-shadow duration-200"
            />
          </div>
        </div>

        {/* Right side actions */}
        <div className="flex items-center space-x-3">
          {/* Dark Mode Toggle */}
          {/* <Button
            variant="ghost"
            size="icon"
            onClick={toggleDarkMode}
            className="hidden lg:flex"
          >
            {isDarkMode ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>

          {/* Notifications */}
          {/* <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-4 w-4" />
            <span className="absolute -top-1 -right-1 h-4 w-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
              2
            </span>
          </Button>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="flex items-center space-x-2 px-2">
                <Avatar className="h-8 w-8">
                  <AvatarImage 
                    src={user?.user_metadata?.avatar_url} 
                    alt={userName}
                  />
                  <AvatarFallback>
                    {getInitials(userName)}
                  </AvatarFallback>
                </Avatar>
                <div className="hidden lg:block text-left">
                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                    {userName}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {userEmail}
                  </div>
                </div>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium">{userName}</p>
                  <p className="text-xs text-gray-500">{userEmail}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              
              <DropdownMenuItem asChild>
                <Link href="/settings/profile" className="flex items-center">
                  <User className="mr-2 h-4 w-4" />
                  Profile Settings
                </Link>
              </DropdownMenuItem>
              
              <DropdownMenuItem asChild>
                <Link href="/settings" className="flex items-center">
                  <Settings className="mr-2 h-4 w-4" />
                  Account Settings
                </Link>
              </DropdownMenuItem>
              
              <DropdownMenuItem className="lg:hidden" onClick={toggleDarkMode}>
                {isDarkMode ? (
                  <>
                    <Sun className="mr-2 h-4 w-4" />
                    Light Mode
                  </>
                ) : (
                  <>
                    <Moon className="mr-2 h-4 w-4" />
                    Dark Mode
                  </>
                )}
              </DropdownMenuItem>
              
              <DropdownMenuSeparator />
              
              <DropdownMenuItem asChild>
                <Link href="/help" className="flex items-center">
                  <HelpCircle className="mr-2 h-4 w-4" />
                  Help & Support
                </Link>
              </DropdownMenuItem>
              
              <DropdownMenuSeparator />
              
              <DropdownMenuItem 
                onClick={handleSignOut}
                className="text-red-600 dark:text-red-400 focus:text-red-600 dark:focus:text-red-400"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}