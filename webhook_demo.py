#!/usr/bin/env python3
"""
Webhook System Demo

This script demonstrates the real-time webhook and WebSocket capabilities
of the slide generation system.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any

# Demo webhook receiver function
async def demo_webhook_receiver(event_data: Dict[str, Any]):
    """
    Demo function that simulates receiving webhook events.
    In a real implementation, this would be your external service endpoint.
    """
    print(f"🔔 Webhook Event: {event_data['event_type']}")
    print(f"   📁 Project: {event_data['project_id']}")
    print(f"   ⏰ Time: {event_data['timestamp']}")
    
    if event_data.get('agent_name'):
        status_emoji = {
            'pending': '⏳',
            'in_progress': '🔄', 
            'completed': '✅',
            'failed': '❌'
        }.get(event_data.get('status', ''), '🔄')
        
        print(f"   🤖 Agent: {event_data['agent_name']}")
        print(f"   {status_emoji} Status: {event_data['status']}")
    
    if event_data.get('data'):
        print(f"   📊 Data: {json.dumps(event_data['data'], indent=6)}")
    print()

async def simulate_workflow_events():
    """Simulate the workflow events that would be sent via webhooks"""
    
    project_id = "demo-project-123"
    
    # Simulate workflow progression
    workflow_steps = [
        {
            "event_type": "project_created",
            "agent_name": None,
            "status": None,
            "data": {
                "title": "Demo Presentation",
                "topic": "AI-Powered Slide Generation"
            }
        },
        {
            "event_type": "workflow_update",
            "agent_name": "layout_analysis",
            "status": "in_progress",
            "data": {"started_at": datetime.now().isoformat()}
        },
        {
            "event_type": "workflow_update", 
            "agent_name": "layout_analysis",
            "status": "completed",
            "data": {
                "execution_time_seconds": 12,
                "layouts_found": 10
            }
        },
        {
            "event_type": "workflow_update",
            "agent_name": "presentation_planning",
            "status": "in_progress",
            "data": {"started_at": datetime.now().isoformat()}
        },
        {
            "event_type": "workflow_update",
            "agent_name": "presentation_planning", 
            "status": "completed",
            "data": {
                "execution_time_seconds": 18,
                "slides_planned": 5
            }
        },
        {
            "event_type": "workflow_update",
            "agent_name": "content_generation",
            "status": "in_progress", 
            "data": {"started_at": datetime.now().isoformat()}
        },
        {
            "event_type": "workflow_update",
            "agent_name": "content_generation",
            "status": "completed",
            "data": {
                "execution_time_seconds": 45,
                "slides_generated": 5
            }
        },
        {
            "event_type": "slide_generated",
            "agent_name": None,
            "status": None,
            "data": {
                "slide_number": 1,
                "title": "Introduction",
                "has_html_content": False
            }
        },
        {
            "event_type": "slide_generated",
            "agent_name": None,
            "status": None,
            "data": {
                "slide_number": 2,
                "title": "Timeline Overview",
                "has_html_content": True
            }
        },
        {
            "event_type": "workflow_update",
            "agent_name": "slide_assembly",
            "status": "in_progress",
            "data": {"started_at": datetime.now().isoformat()}
        },
        {
            "event_type": "workflow_update",
            "agent_name": "slide_assembly",
            "status": "completed",
            "data": {
                "execution_time_seconds": 8,
                "presentation_created": True
            }
        },
        {
            "event_type": "project_completed",
            "agent_name": None,
            "status": "completed",
            "data": {
                "presentation_path": "generated_presentations/demo-project-123.pptx",
                "slide_count": 5,
                "total_execution_time": 83
            }
        }
    ]
    
    print("🚀 Starting Workflow Event Simulation")
    print("=" * 50)
    print()
    
    for step in workflow_steps:
        # Create event data
        event_data = {
            "event_type": step["event_type"],
            "project_id": project_id,
            "agent_name": step["agent_name"],
            "status": step["status"],
            "timestamp": datetime.now().isoformat(),
            "data": step["data"]
        }
        
        # Send to webhook receiver
        await demo_webhook_receiver(event_data)
        
        # Simulate processing time
        await asyncio.sleep(0.5)
    
    print("🎉 Workflow simulation completed!")

def demo_api_integration():
    """Show how to integrate with the webhook API endpoints"""
    
    print("📡 API Integration Examples")
    print("=" * 30)
    print()
    
    # Example webhook registration
    webhook_registration_example = {
        "webhook_url": "https://your-app.com/slide-updates",
        "events": ["workflow_update", "project_completed", "project_failed"],
        "description": "Production notifications"
    }
    
    print("📝 Webhook Registration Example:")
    print("POST /webhooks/register")
    print("Authorization: Bearer YOUR_JWT_TOKEN")
    print("Content-Type: application/json")
    print()
    print(json.dumps(webhook_registration_example, indent=2))
    print()
    
    # Example webhook test
    webhook_test_example = {
        "webhook_url": "https://your-app.com/test-endpoint"
    }
    
    print("🧪 Webhook Test Example:")
    print("POST /webhooks/test")
    print("Authorization: Bearer YOUR_JWT_TOKEN")
    print("Content-Type: application/json")
    print()
    print(json.dumps(webhook_test_example, indent=2))
    print()
    
    # WebSocket connection example
    websocket_example = """
    // JavaScript WebSocket Example
    const projectId = 'your-project-id';
    const jwtToken = 'your-jwt-token';
    
    const ws = new WebSocket(`ws://localhost:8000/ws/${projectId}?token=${jwtToken}`);
    
    ws.onopen = () => {
        console.log('🔗 WebSocket connected');
    };
    
    ws.onmessage = (event) => {
        const update = JSON.parse(event.data);
        console.log('📡 Received update:', update);
        
        // Update your UI based on the event
        updateProgressBar(update);
        showNotification(update);
    };
    
    ws.onclose = () => {
        console.log('🔌 WebSocket disconnected');
    };
    """
    
    print("🌐 WebSocket Connection Example:")
    print(websocket_example)

def main():
    """Run the webhook system demonstration"""
    
    print("🎭 Webhook & Real-time System Demo")
    print("=" * 40)
    print()
    
    # Show API integration examples
    demo_api_integration()
    
    print("\n" + "=" * 40)
    print()
    
    # Run async workflow simulation
    asyncio.run(simulate_workflow_events())
    
    print("\n📚 Next Steps:")
    print("1. Start the API server: python -m uvicorn src.api_server:app --reload")
    print("2. Register webhooks: POST /webhooks/register")
    print("3. Create projects: POST /projects")
    print("4. Connect via WebSocket: ws://localhost:8000/ws/{project_id}")
    print("5. Monitor real-time updates in your frontend!")

if __name__ == "__main__":
    main()