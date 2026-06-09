# Global Configuration

Configure LLM providers and default model settings shared across all projects.

## Add a Provider

1. Navigate to "LLM Providers" in the left sidebar.
2. Click "Add Provider" in the top-right corner.
3. Fill in the provider name, select the provider type (e.g. OpenAI, Anthropic).
4. Enter the API Key (authentication token).
5. Add one or more model names — type a name and press Enter to add.
6. Optionally adjust timeout and max retries.
7. Click "Confirm" to save.

## Set Default Models

1. On the LLM Providers page, find the "Default Model Settings" section at the top.
2. For each role (Planner, Coder, Report, Other), select a provider from the dropdown.
3. After selecting a provider, choose a model from the available models.
4. New tasks will automatically use these default configurations.
