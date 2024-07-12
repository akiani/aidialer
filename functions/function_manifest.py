tools = [
    {
        "type": "function",
        "function": {
            "name": "transfer_call",
            "description": "Transfer call to a human, only do this if the user insists on it.",
            "parameters": {
                "type": "object",
                "properties": {}
            },
            "say": "Transferring your call, please wait."
        }
    },    
    
    {
        "type": "function",
        "function": {
            "name": "end_call",
            "description": "End the current call but always ask for confirmation unless its a natural place in the conversation (and your intent is fullfilled) to end the call.",
            "parameters": {
                "type": "object",
                "properties": {}
            },
            "say": "Goodbye."
        }
    }
]
