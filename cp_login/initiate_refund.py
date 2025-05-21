import stripe


stripe.api_key ='sk_test_51RFbQ6Gace72vhR6HdxrPMjFj1KvWrZBinls5sGwDmCdzLlJhxdrt0jKMK72T5ERW88WzHNLvLxabm0T3bwH3iQ500rL00WMzF'

def initiate_refund(payment_intent_id):
    try:
        # Step 1: Retrieve the PaymentIntent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        # Step 2: Get the associated charge ID
        latest_charge_id = payment_intent.get("latest_charge")
        if not latest_charge_id:
            print(f"❌ No charge found for PaymentIntent: {payment_intent_id}")
            return

        # Step 3: Get metadata from the PaymentIntent
        metadata = payment_intent.get("metadata", {})
        if not metadata:
            print("⚠️ No metadata found on the PaymentIntent.")

        # Step 4: Create the refund with inherited metadata
        refund = stripe.Refund.create(
            charge=latest_charge_id,
            metadata=metadata
        )

        print(f"✅ Refund created successfully for PaymentIntent: {payment_intent_id}")
        print(f"🔁 Refund ID: {refund.id}")
        print(f"📎 Metadata: {refund.metadata}")

    except stripe.StripeError as e:
        print(f"⚠️ Stripe error: {e.user_message}")
    except Exception as e:
        print(f"🚨 Unexpected error: {str(e)}")


# --- Entry Point ---
if __name__ == "__main__":
    user_input = input("Enter the PaymentIntent ID to refund: ").strip()
    if user_input:
        initiate_refund(user_input)
    else:
        print("❌ No PaymentIntent ID provided.")