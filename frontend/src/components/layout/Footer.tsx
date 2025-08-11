'use client'

interface FooterProps {
  className?: string
}

export function Footer({ className }: FooterProps) {
  return (
    <footer className={`bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400 font-light">
            © 2024 Ekona Technologies. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  )
}