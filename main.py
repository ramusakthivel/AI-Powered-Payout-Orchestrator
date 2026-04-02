from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import uvicorn
import requests
import joblib
from datetime import datetime
import numpy as np

app = FastAPI(title="Payout Orchestrator Service")

# 1. Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "payout_db",
    "user": "postgres",
    "password": "Gayu@2393", 
    "port": 5432
}

# 2. Define what a Payout Request looks like (The "Contract")
class PayoutRequest(BaseModel):
    vendor_id: str
    amount: float
    idempotency_key: str

# Load the AI Brain
model = joblib.load('payout_fraud_model.pkl')
encoder = joblib.load('vendor_encoder.pkl')

@app.post("/v1/payouts")
async def create_payout(request: PayoutRequest,x_api_key: str = Header(None)):
    # SIMULATING APIGEE SECURITY POLICY
    if x_api_key != "MY_SECRET_COMPANY_KEY":
        raise HTTPException(status_code=401, detail="Invalid API Key. Apigee would block this!")
    conn = None

    #AI RISK ANALYSIS START 
    current_hour = datetime.now().hour
    
    # We need to handle vendors the model hasn't seen before
    try:
        vendor_encoded = encoder.transform([request.vendor_id])[0]
    except:
        vendor_encoded = -1 # Treat unknown vendors as a neutral value
    
    # The AI predicts: 0 for Safe, 1 for Fraud
    features = [[vendor_encoded, request.amount, current_hour]]
    prediction = model.predict(features)[0]
    probability = model.predict_proba(features)[0][1] # Probability of fraud

    if prediction == 1:
        return {
            "status": "REJECTED_BY_AI",
            "reason": "High Fraud Risk Detected",
            "fraud_probability": round(float(probability), 2)
        }
    #AI RISK ANALYSIS END
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 1. Check Idempotency & Create 'PENDING' record
        cur.execute(
            "SELECT * FROM process_payout_request(%s, %s, %s)",
            (request.vendor_id, request.amount, request.idempotency_key)
        )
        db_result = cur.fetchone()

        # 2. If it's a Duplicate, we stop here.
        if not db_result["is_new_record"]:
            conn.commit()
            return {
                "status": "ALREADY_PROCESSED",
                "message": "This payout was already handled.",
                "payout_details": db_result
            }

        # 3. If it's NEW, call the Bank API (Mockoon)
        try:
            bank_response = requests.post(
                "http://localhost:3000/bank/process-payment",
                json={"vendor": request.vendor_id, "total": request.amount},
                timeout=5 
            )
            
            # Check if the bank returned a 4xx or 5xx error
            bank_response.raise_for_status() 
            bank_data = bank_response.json()

        except requests.exceptions.RequestException as e:
            # The bank is UP, but it rejected the request (e.g., 402)
            if e.response.status_code == 402:
                cur.execute(
                    "UPDATE payouts SET status = %s WHERE payout_id = %s",
                    ('FAILED', db_result["res_payout_id"])
                )
                conn.commit()
                return {"status": "DECLINED", "reason": "Insufficient Funds"}

        # 4. Update the DB with the final Result (Could be SUCCESS or FAILED)
        cur.execute(
            "UPDATE payouts SET status = %s, bank_reference = %s WHERE payout_id = %s",
            (bank_data["payout_status"], bank_data.get("bank_reference"), db_result["res_payout_id"])
        )

        conn.commit()
        
        # Return a different response based on the bank's decision
        if bank_data["payout_status"] == "FAILED":
            return {
                "status": "DECLINED",
                "reason": bank_data.get("error_code", "Unknown Bank Error"),
                "payout_id": db_result["res_payout_id"]
            }

        return {
            "status": "COMPLETED",
            "bank_ref": bank_data["bank_reference"],
            "payout_id": db_result["res_payout_id"]
        }

    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)