# train_model.py
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, classification_report
from sklearn.datasets import make_classification
import xgboost as xgb
import joblib
import numpy as np

print("--- Starting Advanced Model Training Pipeline ---")

# 1. Generate a larger, more realistic synthetic dataset
X, y = make_classification(
    n_samples=20000,        # Increased dataset size
    n_features=4,
    n_informative=3,
    n_redundant=1,
    n_classes=2,
    random_state=42,
    flip_y=0.15             # Increased noise to make it more challenging
)
feature_names = ['cibil_score', 'loan_amount', 'monthly_salary', 'dti_ratio']
df = pd.DataFrame(X, columns=feature_names)
df['will_default'] = y

# 2. Advanced Feature Engineering
# Create new, more powerful features from the existing data to improve model intelligence
print("Step 1: Performing Feature Engineering...")
df['loan_to_income_ratio'] = df['loan_amount'] / (df['monthly_salary'] * 12)
df['emi_to_income_ratio'] = (df['dti_ratio'] * df['monthly_salary']) / df['monthly_salary'] # Simplified for this data
df['high_risk_cibil_flag'] = (df['cibil_score'] < 650).astype(int)

# Update the list of features to include our new, smarter ones
feature_names.extend(['loan_to_income_ratio', 'emi_to_income_ratio', 'high_risk_cibil_flag'])

print(f"Engineered new features. Total features: {len(feature_names)}")

# 3. Split the data for training and testing
X_train, X_test, y_train, y_test = train_test_split(
    df[feature_names], df['will_default'], test_size=0.2, random_state=42
)

# 4. Hyperparameter Tuning with GridSearchCV
# This will automatically test many model configurations to find the best one.
print("Step 2: Searching for the best XGBoost model using GridSearchCV...")
model = xgb.XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss')

# Define the 'grid' of settings for the model to test
param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [3, 5, 7],
    'learning_rate': [0.05, 0.1],
    'subsample': [0.7, 0.9]
}

# Set up the automated search
grid_search = GridSearchCV(
    estimator=model,
    param_grid=param_grid,
    scoring='accuracy',
    cv=3,       # Use 3-fold cross-validation
    verbose=1,
    n_jobs=-1   # Use all available CPU cores to speed up the search
)

# Run the search to find the best model
grid_search.fit(X_train, y_train)

print(f"\nBest parameters found: {grid_search.best_params_}")

# 5. Evaluate the ABSOLUTE BEST model found by the search
best_model = grid_search.best_estimator_
y_pred = best_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"\nStep 3: Evaluating the best model...")
print(f"Final Model Accuracy: {accuracy * 100:.2f}%")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# 6. Save the final, optimized, and more powerful model
joblib.dump(best_model, 'loan_prediction_model.pkl')
print("\n--- Advanced Model Training Complete ---")
print("Optimized XGBoost model saved as 'loan_prediction_model.pkl'")