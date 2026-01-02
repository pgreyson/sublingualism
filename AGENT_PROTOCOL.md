# Agent Protocol

## Critical Rule: Verify Before Declaring Success

**NEVER** announce that a deployment, build, or feature is working without:
1. Checking build/deployment status
2. Verifying the actual output (curl, browser test, etc.)
3. Confirming expected functionality

## Deployment Verification Checklist

When deploying to Amplify or any hosting service:
1. Trigger deployment
2. Wait for build completion
3. Check build status for SUCCESS
4. Test the actual URL with curl or similar
5. Verify expected content appears
6. Only then report success

## Common Pitfalls to Avoid

- Assuming auto-deployment works without verification
- Declaring success based on "should work" logic
- Not checking actual HTTP responses
- Missing build failures in logs

## Error Recovery

When deployments fail:
1. Check build logs immediately
2. Fix the root cause (not symptoms)
3. Re-test after fixes
4. Document issues in SESSION_LOG.md

Remember: Trust but verify. Always.