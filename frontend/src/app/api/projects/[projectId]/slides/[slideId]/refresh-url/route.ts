import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

interface RouteParams {
  params: {
    projectId: string
    slideId: string
  }
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const { projectId, slideId } = await params
    
    // Proxy request to backend refresh URL endpoint
    const backendUrl = `${BACKEND_URL}/projects/${projectId}/slides/${slideId}/refresh-url`
    console.log(`Proxying refresh-url request to: ${backendUrl}`)
    
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Forward any authorization headers if present
        ...(request.headers.get('authorization') && {
          'Authorization': request.headers.get('authorization')!
        })
      },
      // Forward empty body for POST request
      body: JSON.stringify({})
    })

    if (!response.ok) {
      console.error(`Backend refresh-url responded with ${response.status}: ${response.statusText}`)
      return NextResponse.json(
        { error: 'Failed to refresh URL from backend' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('Error proxying refresh-url request:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}