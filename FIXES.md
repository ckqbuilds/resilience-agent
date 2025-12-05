# Bug Fixes - Mode Transition Issues

## Issue: Agent Getting "Caught Up" During Mode Transitions

### Symptoms
1. Mode transition approved successfully
2. User sends new message immediately after
3. Backend returns errors:
   - `400 Bad Request: "No pending interrupt found"`
   - `500 Internal Server Error: "must resume from interrupt with list of interruptResponse's"`

### Root Causes

**Problem 1: Race Condition**
- User could send new messages while mode dialog was active
- Agent was still in interrupted state, but received a string prompt instead of interrupt response

**Problem 2: Missing State Validation**
- Backend didn't prevent new messages when interrupt was pending
- Frontend didn't disable input during mode transition

**Problem 3: Poor Error Messages**
- Generic 400/500 errors didn't explain what went wrong
- Hard to debug session/interrupt state issues

## Fixes Applied

### Backend ([api.py](agent_backend/api.py))

#### Fix 1: Block Messages During Pending Interrupts
```python
# Check if there's a pending interrupt that needs to be resolved first
if session_data.get("pending_interrupt"):
    raise HTTPException(
        status_code=409,
        detail="Cannot send new message while mode transition is pending..."
    )
```
- Returns HTTP 409 (Conflict) if user tries to send message during interrupt
- Clear error message explaining what's wrong

#### Fix 2: Better Error Handling in Interrupt Response
```python
# Validate session exists
if not session_data:
    raise HTTPException(status_code=400, detail=f"Session {request.sessionId} not found")

# Validate pending interrupt exists
if not session_data.get("pending_interrupt"):
    raise HTTPException(
        status_code=400,
        detail="No pending interrupt found. The interrupt may have already been processed..."
    )

# Validate interrupt ID matches
if pending["id"] != request.interruptId:
    raise HTTPException(
        status_code=400,
        detail=f"Interrupt ID mismatch. Expected {pending['id']}, got {request.interruptId}"
    )
```
- Descriptive error messages for each failure case
- Helps debug session and interrupt state issues

#### Fix 3: Handle Nested Interrupts
```python
# Check if the resumed execution also has interrupts
if hasattr(result, 'stop_reason') and hasattr(result, 'interrupts') and result.interrupts:
    # Store new interrupt and return it
    session_data["pending_interrupt"] = { ... }
    return ChatResponse(content="", interrupt={...})
```
- Handles case where agent needs multiple mode transitions
- Example: Planning → Action → Execution requires two approvals

#### Fix 4: Store Conversation Context
```python
sessions[request.sessionId] = {
    "messages": [],
    "pending_interrupt": None,
    "conversation_history": []  # NEW: Track conversation
}
```
- Preserves context for potential future features
- Could enable resume after disconnect

### Frontend ([src/App.tsx](agent_frontend/src/App.tsx))

#### Fix 1: Disable Input During Mode Transition
```tsx
{isLoading || showModeDialog ? (
  <Box>
    <Spinner type="dots" />
    <Text>
      {showModeDialog
        ? 'Waiting for mode approval...'
        : 'Loading...'}
    </Text>
  </Box>
) : (
  <TextInput ... />
)}
```
- Input field replaced with spinner during mode dialog
- Clear message: "Waiting for mode approval..."
- Prevents race condition at the source

#### Fix 2: TypeScript Fixes
- Fixed "Object is possibly 'undefined'" error with optional chaining
- Removed unused React import
- Prefixed unused `input` param with underscore

## Testing the Fix

### Test Case 1: Normal Mode Transition
1. Start conversation: "Discover Lambda resources..."
2. Agent requests mode transition to ACTION
3. Input should be disabled with spinner
4. Approve transition
5. Agent continues and completes task
6. ✅ Input re-enabled after completion

### Test Case 2: Try to Send Message During Transition
1. Start conversation that triggers mode transition
2. Mode dialog appears
3. Try to type in input field
4. ✅ Input is disabled (replaced with spinner)
5. Approve/reject transition
6. ✅ Input re-enabled

### Test Case 3: Multiple Transitions
1. Request action that needs Planning → Action → Execution
2. First transition appears
3. Approve
4. Second transition appears
5. ✅ Each transition handled separately
6. ✅ No race conditions

### Test Case 4: Reject Transition
1. Trigger mode transition
2. Reject the transition
3. ✅ Agent handles rejection gracefully
4. ✅ Can send new messages

## Expected Behavior Now

### Before Fixes
```
User: Discover Lambda and plan FIS experiment
Agent: [Requests ACTION mode]
User: [Approves]
User: Have you created the template? [Sends too quickly]
❌ Error: "No pending interrupt found"
❌ Error: "must resume from interrupt with list..."
```

### After Fixes
```
User: Discover Lambda and plan FIS experiment
Agent: [Requests ACTION mode]
[Input disabled: "Waiting for mode approval..."]
User: [Approves]
Agent: [Completes action]
[Input re-enabled]
User: Have you created the template?
✅ Agent responds normally
```

## API Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 409 | Message sent during pending interrupt | Wait for mode approval |
| 400 | Invalid interrupt response | Session expired, restart |
| 500 | Agent execution error | Check agent logs |

## Rollback Plan

If these changes cause issues:

1. **Backend**: Revert [api.py](agent_backend/api.py) lines 74-79 (pending interrupt check)
2. **Frontend**: Revert [App.tsx](agent_frontend/src/App.tsx) lines 267-276 (input disable logic)

## Future Improvements

- [ ] Add session timeout and cleanup
- [ ] Persist sessions to Redis/database
- [ ] Add retry logic for transient errors
- [ ] Show mode transition history in `/info`
- [ ] Add abort button to cancel pending transitions
- [ ] Implement session recovery after disconnect
