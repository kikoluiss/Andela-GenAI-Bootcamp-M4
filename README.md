# Autonomous Contract Comparison and Change Extraction Agent

## 1. Project Description

This project implements an autonomous system that compares an original contract and its amendment using multimodal large language models. The system processes scanned contract images (PNG/JPEG) and automatically extracts structured information about changes between the original and amended versions. The workflow employs a two-agent architecture where the first agent contextualizes and aligns document sections, while the second agent extracts specific changes, identifies affected legal topics, and generates a concise summary. All operations are instrumented with Langfuse for observability, allowing users to track token usage, latency, and trace the complete execution flow. The system outputs validated JSON results that can be integrated into downstream legal review workflows or contract management systems. The codebase is organized with shared utilities for common operations, centralized configuration management, and a clean separation of concerns between image parsing, agent orchestration, and tracing components.

## 2. Architecture and Agent Workflow

The system follows a sequential pipeline architecture with three main stages:

**Stage 1: Image Parsing**
- Both contract images (original and amendment) are processed by a multimodal LLM (GPT-4.1-mini) that extracts structured sections from the images
- Each section is parsed with an identifier (e.g., "1", "1.1", "2.3"), optional title, and full text content
- This parsing step is individually traced in Langfuse for monitoring and debugging
- The image parser uses shared utility functions for robust JSON extraction and response handling

**Stage 2: Contextualization Agent (Agent 1)**
- The ContextualizationAgent receives the parsed documents and performs structural analysis
- It aligns corresponding sections between the original and amendment documents
- It identifies which sections are new, deleted, moved, or remain unchanged
- Outputs a JSON structure with `aligned_sections` (mapping original to amendment sections) and `structural_notes` (description of document structure differences)
- Uses centralized OpenAI client initialization and shared document serialization utilities

**Stage 3: Change Extraction Agent (Agent 2)**
- The ChangeExtractionAgent receives the original documents, amendment documents, and Agent 1's contextualization output
- It uses this context to identify which specific sections contain actual text modifications
- It extracts the legal/business topics affected by the changes (e.g., payment terms, termination rights, data retention)
- It generates a concise natural language summary of all changes
- The output is validated against a Pydantic model to ensure data quality
- Leverages the same shared utilities for consistent JSON parsing and response handling

**Collaboration Pattern:**
The agents collaborate through a handoff pattern where Agent 1's output becomes part of Agent 2's input context. This separation allows Agent 1 to focus on structural understanding without being distracted by detailed change analysis, while Agent 2 can leverage the alignment information to make more accurate change extractions. All operations are wrapped in Langfuse traces with session IDs and contract IDs for end-to-end observability. The codebase architecture emphasizes code reuse through a shared utilities module (`src/utils.py`) that handles common operations like JSON extraction, response parsing, and document serialization, reducing duplication and improving maintainability.

## 3. Setup Instructions

### Create Virtual Environment (Recommended)

It is recommended to use a Python virtual environment to isolate project dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure API Keys

Create a `.env` file in the project root with the following environment variables:

```bash
# OpenAI API Key (required for multimodal LLM calls)
OPENAI_API_KEY=your_openai_api_key_here

# Langfuse API Keys (required for observability and tracing)
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key_here
LANGFUSE_SECRET_KEY=your_langfuse_secret_key_here

# Optional: Custom Langfuse host (defaults to https://cloud.langfuse.com)
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

**Obtaining API Keys:**
- **OpenAI**: Sign up at [platform.openai.com](https://platform.openai.com) and generate an API key from the API keys section
- **Langfuse**: Sign up at [langfuse.com](https://langfuse.com) or deploy your own instance, then create API keys from the project settings

### Test Images

Place your contract image pairs in the `data/test_contracts/` directory. The system expects:
- Original contract images (e.g., `contract1_original.png`)
- Amendment contract images (e.g., `contract1_amendment.png`)

Sample test contracts are already included in `data/test_contracts/` for validation. See `data/test_contracts/README_test_contracts.md` for details about the test scenarios.

## 4. Usage

Run the contract comparison tool with the following command:

```bash
python -m src.main --original data/test_contracts/contract1_original.png --amendment data/test_contracts/contract1_amendment.png
```

**Optional Arguments:**
- `--session-id`: Custom session identifier for tracing (defaults to a generated UUID)

**Example with custom session ID:**
```bash
python -m src.main --original data/test_contracts/contract1_original.png --amendment data/test_contracts/contract1_amendment.png --session-id "contract-review-2024-01-15"
```

## 5. Expected Output Format

The system outputs a JSON object with the following structure:

```json
{
  "sections_changed": [
    "3.1",
    "3.2",
    "4.5"
  ],
  "topics_touched": [
    "payment terms",
    "subscription fees",
    "late payment interest"
  ],
  "summary_of_the_change": "The amendment increases the monthly subscription fee from USD 10,000 to USD 13,500, shortens the payment deadline from 30 days to 15 days, and raises the late payment interest rate from 1.0% to 1.5% per month."
}
```

**Field Descriptions:**
- `sections_changed`: Array of section identifiers (strings) that contain modifications, additions, or deletions
- `topics_touched`: Array of legal/business topics (strings) affected by the changes, such as "payment terms", "termination rights", "data retention", etc.
- `summary_of_the_change`: A natural language summary (minimum 20 characters) describing all changes in a concise format

**Validation:**
The output is validated using Pydantic models to ensure:
- At least one section is identified as changed
- At least one topic is identified
- The summary is at least 20 characters long

## 6. Technical Decisions

**Why Two Agents?**
The two-agent architecture separates concerns to improve accuracy and maintainability. Agent 1 (ContextualizationAgent) focuses exclusively on structural understanding—aligning sections, identifying document hierarchy, and detecting structural changes like new or deleted sections. This structural analysis is complex enough to warrant a dedicated agent, as contracts may have different numbering schemes, reorganized content, or structural modifications. Agent 2 (ChangeExtractionAgent) then uses this contextual information to perform detailed change extraction. By receiving pre-aligned sections, Agent 2 can focus on semantic differences rather than spending tokens on structural reasoning. This separation also makes the system more debuggable—if structural alignment fails, we can identify the issue at Agent 1's stage, and if change extraction is inaccurate, we know the problem lies in Agent 2's logic.

**Why GPT-4.1-mini?**
GPT-4.1-mini (via OpenAI's Responses API) was chosen for its multimodal capabilities, cost-effectiveness, and performance balance. The system requires vision capabilities to parse scanned contract images, and GPT-4.1-mini provides strong multimodal understanding at a lower cost than GPT-4 Vision. For contract analysis, the model needs to understand legal document structure, extract structured data, and perform comparative analysis—tasks that GPT-4.1-mini handles well. The model's JSON mode support and reliable structured output generation make it suitable for producing the required JSON formats. Additionally, the model's token efficiency is important given that contracts can be lengthy, and we make multiple LLM calls per comparison (image parsing × 2, contextualization, change extraction).

**Code Organization:**
The codebase is organized with a focus on maintainability and code reuse. A shared utilities module (`src/utils.py`) centralizes common operations like JSON extraction from LLM responses, response content parsing, document serialization, and OpenAI client initialization. This eliminates code duplication across agents and the image parser. Configuration constants are centralized in `src/config.py`, including the default model name and Langfuse host settings, making it easy to update defaults across the entire application. This architecture makes the codebase easier to maintain, test, and extend.

## 7. Langfuse Tracing Guide

All operations in the system are automatically traced to Langfuse for observability. To view the traces:

1. **Access the Dashboard**: Log in to your Langfuse account at [cloud.langfuse.com](https://cloud.langfuse.com) (or your custom Langfuse host configured via `LANGFUSE_BASE_URL`)

2. **Navigate to Traces**: Go to the "Traces" section in the left sidebar to see all execution traces

3. **Filter by Session**: Use the session ID (from the `--session-id` argument or auto-generated UUID) to filter traces for a specific contract comparison run

4. **View Trace Details**: Click on any trace to see:
   - The complete workflow with nested spans (image_parsing, agent_contextualization, agent_change_extraction, validation)
   - Input and output data for each operation
   - Token usage and cost information for LLM calls
   - Latency metrics for each stage
   - Metadata including contract_id, agent_name, and session_id

5. **Monitor Performance**: Use the dashboard to identify bottlenecks, track token costs, and debug failures by examining the input/output at each stage

The tracing system is resilient—if Langfuse is unavailable or misconfigured, the system will continue to function (using no-op traces) without breaking the main workflow. The Langfuse client is initialized once at module import time in `src/tracing.py`, using centralized configuration from `src/config.py`.

**Troubleshooting Langfuse Issues:**

If traces are not appearing in your Langfuse dashboard:

1. **Verify API Keys**: Ensure `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are correctly set in your `.env` file and match your Langfuse project settings.

2. **Check Base URL**: Verify that `LANGFUSE_BASE_URL` is set correctly (defaults to `https://cloud.langfuse.com` for cloud, or your custom host URL if self-hosted).

3. **Enable Logging**: The system logs Langfuse initialization status. Check for warnings like "Langfuse API keys not found" or "Failed to initialize Langfuse client" in your application logs.

4. **Manual Flush**: The system automatically flushes data at the end of each operation and before application exit. For very short-lived scripts, you can manually call `flush_langfuse()` from `src.tracing`.

5. **Network Connectivity**: Ensure your network allows outbound connections to Langfuse endpoints and that there are no firewall restrictions.

6. **Check Dashboard**: Traces may take a few seconds to appear. Refresh your Langfuse dashboard and check the correct project is selected.
