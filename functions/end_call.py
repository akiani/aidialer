import os
from twilio.rest import Client
import asyncio

async def end_call(context, args):
    # Retrieve the Twilio credentials from environment variables
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    client = Client(account_sid, auth_token)
    call_sid = context.call_sid

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