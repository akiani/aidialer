import os
from twilio.rest import Client

async def transfer_call(args):
    department = args.get('department')
    
    # Retrieve the active call using the CallSid
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    client = Client(account_sid, auth_token)

    # Assuming the CallSid is stored in an environment variable
    call_sid = os.environ.get('CURRENT_CALL_SID')

    if not call_sid:
        return "Error: No active call found"

    try:
        call = client.calls(call_sid).fetch()
        
        # Define transfer numbers for different departments
        transfer_numbers = {
            "billing": "+1234567890",
            "customer_service": "+1987654321",
            # Add more departments as needed
        }

        if department.lower() in transfer_numbers:
            transfer_number = transfer_numbers[department.lower()]
            
            # Update the call with the new number
            call = client.calls(call_sid).update(
                url=f'http://twimlets.com/forward?PhoneNumber={transfer_number}',
                method='POST'
            )
            
            return f"Call transferred to {department} department."
        else:
            return f"Error: Department '{department}' not found."

    except Exception as e:
        return f"Error transferring call: {str(e)}"