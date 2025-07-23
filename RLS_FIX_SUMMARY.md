# Row Level Security (RLS) Policy Fix Summary

## Problem Description

The backend API was experiencing RLS (Row Level Security) policy violations when trying to create projects in Supabase. The error message was:

```
Error: "new row violates row-level security policy for table 'projects'"
```

## Root Cause Analysis

The issue occurred because:

1. **Backend Authentication Approach**: The backend was using `SUPABASE_ANON_KEY` to connect to Supabase
2. **RLS Policy Requirements**: The RLS policies check `auth.uid() = user_id` for access control
3. **Missing User Context**: When using anon key without setting user context, `auth.uid()` returns null
4. **Service Role Key**: The system wasn't configured to use the service role key for backend operations

## Solution Implemented

### 1. Enhanced Database Client Configuration

**File**: `src/database.py`

- **Service Role Key Priority**: Modified the Supabase client initialization to prefer `SUPABASE_SERVICE_ROLE_KEY` over `SUPABASE_ANON_KEY`
- **Key Type Detection**: Added logging to show whether service role or anon key is being used
- **Bypass RLS**: When service role key is used, RLS policies are automatically bypassed

```python
# Prefer service role key for backend operations to bypass RLS
self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
self.using_service_role = bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
```

### 2. User Context Management

**File**: `src/database.py`

- **User Client Creation**: Added method to create user-specific Supabase clients when needed
- **JWT Token Handling**: When using anon key, create clients with proper JWT token authorization
- **Flexible Operation**: Database operations can now work with or without service role key

```python
def create_user_client(self, jwt_token: str) -> Client:
    """Create a Supabase client with user context for RLS operations"""
    if self.using_service_role:
        return self.client  # Bypass RLS
    else:
        # Create client with JWT token for RLS compliance
        return create_client(
            self.supabase_url, 
            os.getenv("SUPABASE_ANON_KEY"),
            options=ClientOptions(headers={"Authorization": f"Bearer {jwt_token}"})
        )
```

### 3. API Server Updates

**File**: `src/api_server.py`

- **JWT Token Passing**: Modified key API endpoints to pass JWT tokens to database operations
- **Authentication Flow**: Improved authentication to work with both service role and anon key scenarios
- **Error Handling**: Enhanced error messages for debugging authentication issues

### 4. Database Operation Updates

Updated key database methods to accept optional JWT tokens:

- `create_project()` - Now accepts `jwt_token` parameter
- `get_project()` - Now accepts `jwt_token` parameter  
- `get_user_projects()` - Now accepts `jwt_token` parameter

## Environment Variable Configuration

### Required Variables

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
```

### Recommended for Backend Operations

```env
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

## Benefits of This Solution

### With Service Role Key (Recommended)
- ✅ **Bypasses RLS**: No RLS policy violations
- ✅ **Better Performance**: No need to create multiple clients
- ✅ **Simplified Architecture**: Single client handles all operations
- ✅ **Backend Security**: Service role key only used server-side

### With Anon Key (Fallback)
- ✅ **RLS Compliant**: Creates user-specific clients with JWT tokens
- ✅ **Secure**: Respects all RLS policies
- ✅ **Backward Compatible**: Works with existing setups

## Testing

A test script has been created to verify the configuration:

```bash
python test_database_connection.py
```

This script will:
- ✅ Check environment variables
- ✅ Test database connectivity
- ✅ Verify RLS policy handling
- ✅ Test project creation operations

## Verification Steps

1. **Set Environment Variables**: Ensure `SUPABASE_SERVICE_ROLE_KEY` is set
2. **Run Tests**: Execute the test script to verify configuration
3. **Start API Server**: Run `python src/api_server.py`
4. **Test API Endpoints**: Try creating a project through the API
5. **Check Logs**: Verify that "service_role" key is being used in logs

## RLS Policies Status

The existing RLS policies in `database-setup.sql` remain unchanged:

```sql
-- Projects table policies
CREATE POLICY "Users can insert their own projects" ON projects
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view their own projects" ON projects
    FOR SELECT USING (auth.uid() = user_id);
```

These policies work correctly with the new implementation:
- **Service Role Key**: Bypasses RLS entirely (secure for backend operations)
- **Anon Key**: Uses JWT token to set proper user context for RLS compliance

## Migration Steps

1. **Add Service Role Key**: Set `SUPABASE_SERVICE_ROLE_KEY` in your environment
2. **Restart Backend**: Restart the API server to pick up the new configuration
3. **Test Operations**: Verify that project creation now works
4. **Monitor Logs**: Check that "service_role" appears in initialization logs

## Security Considerations

- **Service Role Key**: Only used server-side, never exposed to client
- **JWT Validation**: User authentication still validated through proper JWT verification
- **RLS Bypass**: Service role operations bypass RLS by design (this is expected and secure)
- **User Context**: When using anon key, proper user context is maintained for RLS

## Troubleshooting

### If Still Getting RLS Errors:
1. Verify `SUPABASE_SERVICE_ROLE_KEY` is set correctly
2. Check that service role key has proper permissions in Supabase dashboard
3. Ensure API server is restarted after environment changes
4. Run the test script to diagnose issues

### Common Issues:
- **Wrong Service Role Key**: Double-check the key from Supabase dashboard
- **Environment Not Loaded**: Ensure .env file is in correct location
- **Caching Issues**: Restart the application completely
- **Network Issues**: Verify Supabase service is accessible

## Files Modified

- `src/database.py` - Enhanced database client with service role support
- `src/api_server.py` - Updated authentication and JWT token handling
- `test_database_connection.py` - New test script for verification
- `RLS_FIX_SUMMARY.md` - This documentation file

The fix ensures robust authentication that works in both development and production environments while maintaining security best practices.