import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Workflow | Ekona Slide Creator',
  description: 'Monitor slide generation workflow progress',
}

export default function WorkflowPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Workflow Progress
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Monitor the progress of your slide generation workflows
        </p>
      </div>

      <div className="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
        <p className="text-center text-gray-600 dark:text-gray-400">
          Workflow progress monitoring interface will be implemented here
        </p>
        
        {/* TODO: Implement WorkflowProgress component */}
        {/* <WorkflowProgress /> */}
      </div>
    </div>
  )
}