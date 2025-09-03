# Repository Instructions

## Updating Agent-SDK SHA

If the user says something along the lines of "update the sha" or "update the agent-sdk sha", you need to:

1. Use the `$GITHUB_TOKEN` to get the latest commit from the agent-sdk repository
2. Update the poetry toml file with the new SHA
3. Regenerate the uv lock file
4. Run `./build.sh` to confirm that the build still works
5. Open a pull request with the changes

If the build fails, still open the pull request and explain what error you're seeing, and the steps you plan to take to fix it; don't fix it yet though.