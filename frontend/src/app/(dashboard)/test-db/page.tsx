'use client'

import { useEffect, useState } from 'react'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function TestDbPage() {
  const { supabase, user } = useSupabaseAuth()
  const [testResult, setTestResult] = useState<string>('')

  const testDatabase = async () => {
    setTestResult('Testing database connection...\n')
    
    try {
      // Test 1: Check if we can connect to Supabase
      const { data: { user: currentUser }, error: userError } = await supabase.auth.getUser()
      setTestResult(prev => prev + `✓ User connection: ${currentUser?.email || 'No user'}\n`)

      // Test 2: Try to query projects table
      const { data: projects, error: projectsError } = await supabase
        .from('projects')
        .select('*')
        .limit(1)

      if (projectsError) {
        setTestResult(prev => prev + `✗ Projects table error: ${JSON.stringify(projectsError)}\n`)
      } else {
        setTestResult(prev => prev + `✓ Projects table exists, found ${projects?.length || 0} records\n`)
      }

      // Test 3: Try to create a test project
      if (!projectsError && user) {
        const { data: newProject, error: createError } = await supabase
          .from('projects')
          .insert({
            user_id: user.id,
            title: 'Test Project',
            topic: 'This is a test project created to verify database functionality',
            status: 'draft'
          })
          .select()
          .single()

        if (createError) {
          setTestResult(prev => prev + `✗ Create project error: ${JSON.stringify(createError, null, 2)}\n`)
        } else {
          setTestResult(prev => prev + `✓ Test project created successfully: ${newProject?.id}\n`)
          
          // Clean up - delete the test project
          await supabase
            .from('projects')
            .delete()
            .eq('id', newProject.id)
          setTestResult(prev => prev + `✓ Test project cleaned up\n`)
        }
      }

    } catch (error) {
      setTestResult(prev => prev + `✗ Unexpected error: ${JSON.stringify(error)}\n`)
    }
  }

  return (
    <div className="p-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Database Connection Test</CardTitle>
        </CardHeader>
        <CardContent>
          <Button onClick={testDatabase} className="mb-4">
            Test Database
          </Button>
          {testResult && (
            <pre className="bg-gray-100 p-4 rounded-md text-sm font-mono whitespace-pre-wrap">
              {testResult}
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  )
}