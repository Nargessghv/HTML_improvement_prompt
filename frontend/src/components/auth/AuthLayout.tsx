'use client'

import { ReactNode } from 'react'
import Link from 'next/link'

interface AuthLayoutProps {
  children: ReactNode
  title?: string
  subtitle?: string
}

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left side - Branding */}
      <div className="hidden lg:flex flex-col justify-center items-center bg-gradient-to-br from-ekona-teal via-ekona-blue to-ekona-purple p-12 relative overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 w-32 h-32 border border-white rounded-full" />
          <div className="absolute top-32 right-20 w-24 h-24 border border-white rounded-lg rotate-45" />
          <div className="absolute bottom-20 left-20 w-40 h-40 border border-white rounded-full" />
          <div className="absolute bottom-32 right-16 w-28 h-28 border border-white rounded-lg -rotate-12" />
        </div>

        <div className="relative z-10 max-w-md text-center text-white">
          {/* Logo */}
          <div className="mb-8">
            <Link href="/" className="inline-block">
              <div className="text-4xl font-bold text-white mb-2">
                Ekona
              </div>
              <div className="text-xl font-medium text-white/90">
                Slide Creator
              </div>
            </Link>
          </div>

          {/* Marketing content */}
          <div className="space-y-6">
            <h1 className="text-3xl font-bold leading-tight">
              AI-Powered Presentations in Minutes
            </h1>
            
            <p className="text-lg text-white/90 leading-relaxed">
              Transform your ideas into stunning PowerPoint presentations with our advanced AI agents. 
              Just describe your topic and watch as we create professional slides tailored to your needs.
            </p>

            <div className="grid grid-cols-1 gap-4 pt-6">
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-white rounded-full flex-shrink-0" />
                <span className="text-sm text-white/90">7 specialized AI agents working together</span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-white rounded-full flex-shrink-0" />
                <span className="text-sm text-white/90">Real-time progress tracking</span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-white rounded-full flex-shrink-0" />
                <span className="text-sm text-white/90">Interactive HTML editing</span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-white rounded-full flex-shrink-0" />
                <span className="text-sm text-white/90">Professional Ekona branding</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Auth form */}
      <div className="flex flex-col justify-center items-center p-8 bg-gray-50">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden mb-8 text-center">
            <Link href="/" className="inline-block">
              <div className="text-2xl font-bold text-ekona-teal mb-1">
                Ekona Slide Creator
              </div>
              <div className="text-sm text-muted-foreground">
                AI-Powered Presentations
              </div>
            </Link>
          </div>

          {/* Optional title and subtitle */}
          {(title || subtitle) && (
            <div className="text-center mb-8 lg:hidden">
              {title && (
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                  {title}
                </h1>
              )}
              {subtitle && (
                <p className="text-gray-600">
                  {subtitle}
                </p>
              )}
            </div>
          )}

          {/* Auth form */}
          {children}

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-xs text-muted-foreground">
              © {new Date().getFullYear()} Ekona. All rights reserved.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}