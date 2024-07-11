import os
from twilio.rest import Client
import asyncio

async def transfer_call(context, args):
    # Retrieve the active call using the CallSid
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    transfer_number = os.environ['TRANSFER_NUMBER']

    client = Client(account_sid, auth_token)
    call_sid = context.call_sid

    # Wait for 10 seconds before transferring the call
    await asyncio.sleep(8)

    try:
        call = client.calls(call_sid).fetch()
        
        # Update the call with the transfer number
        call = client.calls(call_sid).update(
            url=f'http://twimlets.com/forward?PhoneNumber={transfer_number}',
            method='POST'
        )
            
        return f"Call transferred."

    except Exception as e:
        return f"Error transferring call: {str(e)}"