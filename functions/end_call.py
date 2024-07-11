import os
from twilio.rest import Client
import asyncio

async def end_call(args):
    # Retrieve the Twilio credentials from environment variables
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    client = Client(account_sid, auth_token)

    # Assuming the CallSid is stored in an environment variable
    call_sid = os.environ.get('CURRENT_CALL_SID')

    if not call_sid:
        return "Error: No active call found"

    try:
        # Fetch the call
        call = client.calls(call_sid).fetch()

        # Check if the call is already completed
        if call.status in ['completed', 'failed', 'busy', 'no-answer', 'canceled']:
            return f"Call already ended with status: {call.status}"

        # Wait for 5 seconds before ending the call to ensure the goodbye goes through
        await asyncio.sleep(5)

        # End the call
        call = client.calls(call_sid).update(status='completed')

        return f"Call ended successfully. Final status: {call.status}"

    except Exception as e:
        return f"Error ending call: {str(e)}"