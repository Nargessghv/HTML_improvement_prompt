import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Settings | Ekona Slide Creator',
  description: 'Configure your account and application settings',
}

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Settings
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Configure your account and application preferences
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Account Settings
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Account settings interface will be implemented here
          </p>
        </div>

        <div className="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Application Preferences
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Application preferences interface will be implemented here
          </p>
        </div>
      </div>
    </div>
  )
}