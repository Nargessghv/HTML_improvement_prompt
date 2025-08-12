import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

interface RouteParams {
  params: {
    projectId: string
    slideId: string
  }
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { projectId, slideId } = await params
    
    // Proxy request to backend
    const backendUrl = `${BACKEND_URL}/projects/${projectId}/slides/${slideId}`
    
    // Try both lowercase and capitalized authorization headers
    const authHeader = request.headers.get('authorization') || request.headers.get('Authorization')
    
    console.log(`Proxying GET request to: ${backendUrl}`)
    console.log(`Authorization header present: ${!!authHeader}`)
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    
    if (authHeader) {
      headers['Authorization'] = authHeader
      console.log(`Forwarding auth header: ${authHeader.substring(0, 20)}...`)
    } else {
      console.warn('No authorization header found in request')
      console.warn('Request headers:', Array.from(request.headers.entries()))
    }
    
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error(`Backend responded with ${response.status}: ${response.statusText}`)
      console.error(`Backend error: ${errorText}`)
      
      // Try to parse as JSON if possible
      try {
        const errorJson = JSON.parse(errorText)
        return NextResponse.json(errorJson, { status: response.status })
      } catch {
        return NextResponse.json(
          { error: 'Failed to fetch slide data from backend', details: errorText },
          { status: response.status }
        )
      }
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('Error proxying slide request:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}