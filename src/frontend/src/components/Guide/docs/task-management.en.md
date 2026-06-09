# Task Management

Create, configure, run, and analyze evolution tasks within your projects.

## Create a Task

1. Enter a project from the Projects page.
2. Click "New Task" in the left task list panel.
3. Enter a task name and optionally select a template.
4. Click "Confirm" to create the task.

## Configure Parameters (Step by Step)

New tasks enter the configuration wizard automatically. Follow these steps:

### Step 1: Data Preparation

Upload the required files (fitness function, datasets). Click "Upload Directory" to select a folder, check the files to upload, then confirm. You can edit files after uploading.

### Step 2: LLM Providers

Select providers and models for the Planner and Coder roles. If left unset, system defaults will be used. You can also click "Configure Providers" to jump to the global provider settings.

### Step 3: Evaluator

Configure the fitness evaluation method. Set the evaluation function entry point, timeout, and other evaluation parameters.

### Step 4: Evolution Algorithm

Choose the evolution algorithm type (e.g. island model). Adjust population size, number of iterations, selection strategy, and other hyperparameters.

### Step 5: Code Generation

Configure code generation strategy, prompt templates, and related parameters for the Coder component.

### Step 6: Advanced Components

Configure memory management, logging, workspace paths, and version control. Default values usually work fine.

### Step 7: Parameter Confirmation

Review the full YAML configuration. You can edit directly, import/export YAML files. Click "Submit" to start the task.

## Run a Task

1. After configuring parameters, click "Submit" on the confirmation step.
2. The task enters "Pending" then "Running" status.
3. Watch the evolution simulation in real-time on the main visualization panel.
4. Use the progress bar at the bottom to navigate between generations.
5. Click "Stop" in the right panel to halt a running task.

## View Parameters, Results & Logs

1. Click "View Parameters" in the right panel to see the read-only configuration.
2. Switch to the "Logs" tab in the right panel to view real-time run logs.
3. Click nodes in the visualization to view algorithm details, fitness scores, and lineage.
4. Use the trend analysis panel to track score progression across generations.

## Insight Reports

1. Switch to the "Insights" tab in the main content area.
2. Select a report type: Overall Summary, Node Comparison, Chain Analysis, or Optimal Algorithm Analysis.
3. Select the required nodes (varies by report type).
4. Optionally choose a specific provider/model for report generation.
5. Click "Generate Report" and wait for the AI-generated analysis.
