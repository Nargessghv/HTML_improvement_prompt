import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Projects | Ekona Slide Creator',
  description: 'Manage your slide creator projects',
}

export default function ProjectsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Projects
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Manage and create new slide presentations
          </p>
        </div>
        
        <div className="text-sm text-gray-600 dark:text-gray-400">
          New Project button will be implemented here
        </div>
      </div>

      <div className="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
        <p className="text-center text-gray-600 dark:text-gray-400">
          Project list and management interface will be implemented here
        </p>
        
        {/* TODO: Implement ProjectList component */}
        {/* <ProjectList /> */}
      </div>
    </div>
  )
}