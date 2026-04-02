import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib

# 1. Load Data
df = pd.read_csv('payout_data.csv')

# 2. Preprocess: Convert 'Vendor_ID' string to a number the AI understands
le = LabelEncoder()
df['vendor_id_encoded'] = le.fit_transform(df['vendor_id'])

# 3. Features (X) and Target (y)
X = df[['vendor_id_encoded', 'amount', 'hour']]
y = df['is_fraud']

# 4. Split and Train
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# 5. Save the Model and the Encoder
joblib.dump(model, 'payout_fraud_model.pkl')
joblib.dump(le, 'vendor_encoder.pkl')

print(f"Model trained! Accuracy: {model.score(X_test, y_test):.2f}")