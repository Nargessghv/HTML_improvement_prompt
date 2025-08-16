# Azure Graph API Setup for Thumbnail Generation

Since your users already authenticate with Azure AD, we can leverage their authentication for Microsoft Graph API thumbnail generation.

## 🎯 Overview

The system will use your users' existing Azure AD tokens to:
1. Upload PPTX files to their OneDrive temporarily
2. Convert PPTX to PDF using Microsoft Graph API
3. Download the PDF and convert to PNG thumbnail
4. Clean up temporary files

## 🔧 Step 1: Update Your Azure App Registration

### Add Microsoft Graph Permissions

In Azure Portal → App Registrations → Your App → API Permissions:

1. **Add a permission** → **Microsoft Graph** → **Delegated permissions**
2. **Add these permissions:**
   - `Files.ReadWrite` - Read and write user files
   - `Sites.ReadWrite.All` - Read and write items in all site collections (alternative)

3. **Grant admin consent** for these permissions

### Alternative via Azure CLI:
```bash
# Get your app ID
APP_ID=$(az ad app list --display-name "your-app-name" --query "[0].appId" -o tsv)

# Add Files.ReadWrite permission
az ad app permission add --id $APP_ID \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions 75359482-378d-4052-8f01-80520e7db3cd=Scope

# Grant admin consent
az ad app permission admin-consent --id $APP_ID
```

## 🔧 Step 2: Update Frontend Authentication

### Modify Login Scopes

Update your frontend authentication to request Graph API scopes:

```typescript
// In your Azure AD login configuration
const loginRequest = {
  scopes: [
    "openid", 
    "profile", 
    "email",
    "https://graph.microsoft.com/Files.ReadWrite",  // NEW: For OneDrive access
    "https://graph.microsoft.com/Sites.ReadWrite.All"  // NEW: For SharePoint access
  ]
};

// Use this when calling acquireTokenSilent or loginPopup
```

### Frontend Token Passing

When calling your backend API, include the user's access token:

```typescript
// Get token with Graph scopes
const tokenRequest = {
  scopes: ["https://graph.microsoft.com/Files.ReadWrite"],
  account: account // user's account
};

const response = await msalInstance.acquireTokenSilent(tokenRequest);
const accessToken = response.accessToken;

// Pass to backend API
const apiResponse = await fetch('/api/generate-slide', {
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'X-Graph-Token': accessToken  // Pass Graph token separately
  },
  // ... other options
});
```

## 🔧 Step 3: Update Backend Code

### API Server Changes

Update your FastAPI server to extract and pass user tokens:

```python
# In your API endpoint
from fastapi import Header
from typing import Optional

@app.post("/api/generate-slide")
async def generate_slide(
    x_graph_token: Optional[str] = Header(None)  # Extract Graph token
):
    # Pass user token to thumbnail generator
    thumbnail_path = thumbnail_generator.generate_thumbnail(
        pptx_path=pptx_path,
        user_access_token=x_graph_token  # Pass user's token
    )
```

### Individual Slide Generator Changes

Update the thumbnail generation call:

```python
# In individual_slide_generator.py
async def generate_individual_slide(
    self,
    slide_id: str,
    project_id: str,
    slide_content: SlideContent,
    template_path: str,
    slide_number: int,
    user_access_token: Optional[str] = None,  # NEW parameter
    # ... other params
):
    # Generate thumbnail with user token
    thumbnail_path = self.thumbnail_generator.generate_thumbnail(
        pptx_path=individual_pptx_path,
        size=(800, 600),
        slide_number=0,
        user_access_token=user_access_token  # Pass user token
    )
```

## 🔧 Step 4: Environment Configuration

### Update .env file:

```env
# Existing Azure credentials (for client credentials fallback)
AZURE_CLIENT_ID=your_azure_app_client_id
AZURE_CLIENT_SECRET=your_azure_app_client_secret
AZURE_TENANT_ID=your_azure_tenant_id

# Optional: For testing with a user token
AZURE_USER_ACCESS_TOKEN=user_token_for_testing
```

## 🔧 Step 5: Testing

### Test with User Token

1. **Get a user access token:**
   - Go to [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)
   - Sign in with your account
   - Run a query like `GET https://graph.microsoft.com/v1.0/me`
   - Copy the access token from the "Access token" tab

2. **Add to .env for testing:**
   ```env
   AZURE_USER_ACCESS_TOKEN=eyJ0eXAiOiJKV1QiLCJub25jZSI6...
   ```

3. **Run test:**
   ```bash
   python test_graph_thumbnail.py
   ```

## 📋 Permission Requirements Summary

### Delegated Permissions (User context):
- ✅ `Files.ReadWrite` - Access user's OneDrive
- ✅ `Sites.ReadWrite.All` - Access SharePoint sites

### NOT Application Permissions:
- ❌ Don't use `Files.ReadWrite.All` (application permission)
- ❌ Client credentials flow won't work for `/me` endpoints

## 🚀 Production Deployment

### For Cloud Deployment:

1. **No LibreOffice dependency** - Graph API handles conversion
2. **Scales automatically** - Microsoft handles the infrastructure
3. **Secure** - Uses user's own OneDrive, no permanent file storage
4. **Fast** - Native Office conversion engine

### Architecture Flow:

```
User Authentication (Frontend)
       ↓
   Gets Graph Token
       ↓
   Calls Backend API
       ↓
   Backend uses User Token
       ↓
   Microsoft Graph API
   (Upload → Convert → Download)
       ↓
   PDF2Image (Local)
       ↓
   Thumbnail Generated
```

## 🛠️ Troubleshooting

### Common Issues:

1. **403 Forbidden**: User hasn't consented to Graph permissions
   - Solution: Update frontend scopes and re-authenticate

2. **401 Unauthorized**: Token doesn't have Graph scopes
   - Solution: Ensure frontend requests Graph-scoped tokens

3. **404 Not Found**: Using client credentials for `/me` endpoints
   - Solution: Use delegated user tokens instead

4. **400 Bad Request**: Invalid file upload
   - Solution: Check file size limits and content-type headers

## 📝 Next Steps

1. Update your Azure app registration with Graph permissions
2. Modify frontend to request Graph scopes during login
3. Update backend to accept and use user tokens
4. Test with a real user token
5. Deploy to production

This approach leverages your existing Azure AD authentication and provides a cloud-native, scalable solution for thumbnail generation!