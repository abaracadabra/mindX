
# mindX Gemini-CLI Integration Hook
# Reference: https://geminicli.com/docs/hooks/writing-hooks/

import sys
import os
import json

def pre_generate(context):
    """
    Invoked before sending the prompt to Gemini.
    Injects mindX substrate context into the prompt.
    """
    # Simulate fetching context from the epistemic layer
    # In production, this would call the mindX backend API
    substrate_context = {
        "active_persona": os.getenv("MINDX_PERSONA", "suntsu"),
        "quorum_status": "SUPERMAJORITY_LOCKED",
        "current_terrain": "HIGH_GROUND"
    }
    
    # Prepend context to the user's prompt
    context['prompt'] = f"[SUBSTRATE_CONTEXT: {json.dumps(substrate_context)}]\n\n" + context['prompt']
    return context

def post_generate(response):
    """
    Invoked after the response is received.
    Can be used to log the decree back to the telemetry feed.
    """
    # Send response metadata to mindX telemetry
    # print(f"// DECREE_LOGGED: {response['text'][:50]}...", file=sys.stderr)
    return response
