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
    
    // Proxy request to backend download endpoint
    const backendUrl = `${BACKEND_URL}/projects/${projectId}/slides/${slideId}/download`
    console.log(`Proxying download request to: ${backendUrl}`)
    
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        // Forward any authorization headers if present
        ...(request.headers.get('authorization') && {
          'Authorization': request.headers.get('authorization')!
        })
      }
    })

    if (!response.ok) {
      console.error(`Backend download responded with ${response.status}: ${response.statusText}`)
      
      // If backend returns JSON error, forward it
      const contentType = response.headers.get('content-type')
      if (contentType?.includes('application/json')) {
        const errorData = await response.json()
        return NextResponse.json(errorData, { status: response.status })
      }
      
      return NextResponse.json(
        { error: 'Failed to download slide from backend' },
        { status: response.status }
      )
    }

    // For file downloads, we need to stream the response
    const contentType = response.headers.get('content-type') || 'application/octet-stream'
    const contentDisposition = response.headers.get('content-disposition')
    
    // If backend returns a redirect, return the redirect URL to frontend as JSON
    if (response.status === 302 || response.status === 301) {
      const location = response.headers.get('location')
      if (location) {
        return NextResponse.json({ redirect_url: location })
      }
    }
    
    // For direct file content, stream it
    if (response.body) {
      const headers = new Headers()
      headers.set('Content-Type', contentType)
      if (contentDisposition) {
        headers.set('Content-Disposition', contentDisposition)
      }
      
      return new NextResponse(response.body, {
        status: 200,
        headers
      })
    }

    // Fallback - if no body, assume it's a JSON response with download URL
    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('Error proxying slide download:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}