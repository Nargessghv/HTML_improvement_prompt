export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* TODO: Implement Navigation/Header component */}
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              Ekona Slide Creator
            </h1>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Dashboard navigation will be implemented here
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* TODO: Implement Sidebar component */}
        <aside className="w-64 bg-white dark:bg-gray-800 shadow-sm">
          <div className="p-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Sidebar navigation will be implemented here
            </p>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  )
}