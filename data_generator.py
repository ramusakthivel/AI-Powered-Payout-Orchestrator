import pandas as pd
import numpy as np
import random

def generate_payout_data(records=1000):
    data = []
    vendors = ['VNDR_MURA_001', 'VNDR_MURA_002', 'VNDR_TRUSTED_01', 'VNDR_NEW_99', 'VNDR_SUSP_66']

    for i in range(records):
        vendor = random.choice(vendors)
        amount = round(random.uniform(10, 50000), 2)
        hour = random.randint(0, 23) # Time of day

        # LOGIC FOR FAKE FRAUD (The labels the AI will learn)
        is_fraud = 0
        if amount > 25000: is_fraud = 1 # High amount risk
        if hour >= 1 and hour <= 4: is_fraud = 1 # Night time risk
        if "SUSP" in vendor: is_fraud = 1 # Blacklisted vendor risk

        # Add some "Noise" (Randomness) so it's not too easy for the AI
        if random.random() < 0.05: is_fraud = 1 - is_fraud

        data.append([vendor, amount, hour, is_fraud])

    df = pd.DataFrame(data, columns=['vendor_id', 'amount', 'hour', 'is_fraud'])
    df.to_csv('payout_data.csv', index=False)
    print("Dataset 'payout_data.csv' created with 1000 records!")

if __name__ == "__main__":
    generate_payout_data()