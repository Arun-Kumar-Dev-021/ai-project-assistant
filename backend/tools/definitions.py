"""
Claude tool definitions — these are passed to the API so Claude
can call memory, search, and image-analysis tools during chat.
"""

TOOLS = [
    {
        "name": "save_memory",
        "description": (
            "Save an important piece of information about the project to long-term memory. "
            "Use this whenever the user mentions goals, decisions, preferences, tech choices, "
            "deadlines, team members, or any context that should be remembered in future sessions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Short unique identifier for this memory (e.g. 'main_goal', 'tech_stack', 'deadline')"
                },
                "value": {
                    "type": "string",
                    "description": "The information to remember."
                },
                "category": {
                    "type": "string",
                    "enum": ["goal", "decision", "context", "note", "technical", "team", "general"],
                    "description": "Category of memory."
                }
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "get_memory",
        "description": (
            "Retrieve all saved memories for the current project. "
            "ALWAYS call this at the start of a conversation to recall what you already know."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional: filter by category. Leave empty to get all."
                }
            }
        }
    },
    {
        "name": "generate_image",
        "description": (
            "Generate an image based on a text prompt. "
            "Use when the user asks to create, visualize, or generate any image."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed image generation prompt."
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "analyze_image",
        "description": (
            "Use Gemini to analyze an image that was previously generated or uploaded. "
            "Use when the user asks questions about an image."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "image_id": {
                    "type": "string",
                    "description": "The UUID of the image stored in the database."
                },
                "question": {
                    "type": "string",
                    "description": "What the user wants to know about the image."
                }
            },
            "required": ["image_id", "question"]
        }
    },
    {
        "name": "list_project_images",
        "description": "List all images associated with the current project.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "search_web",
        "description": (
            "Search the web for current information relevant to the project. "
            "Use when the user asks for research, documentation, or latest news."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query."
                }
            },
            "required": ["query"]
        }
    }
]
