from plan_eligibility import evaluate_plan, PlanEligibilityEvaluator

def test_plan_eligibility():
    # Test parameters
    api_key = "a499cbf2c1d130bca9416e482e8c18db"
    plan_id = "53901AZ1420001"  # A plan ID from the PUF file
    zip_code = "85001"  # Phoenix, AZ zip code since it's an AZ plan
    year = 2025
    puf_file = "business-rules-puf 2.csv"
    
    try:
        print(f"Evaluating plan {plan_id} for zip code {zip_code} in year {year}...")
        
        # Create evaluator to access the API response
        evaluator = PlanEligibilityEvaluator(api_key, puf_file)
        api_data = evaluator.get_plan_details(plan_id, zip_code, year)
        print("\nAPI Response:")
        print(api_data)
        
        # Get eligibility criteria
        criteria = evaluate_plan(api_key, plan_id, zip_code, year, puf_file)
        
        print("\nEligibility Criteria:")
        for bullet in criteria:
            print(bullet)
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_plan_eligibility() 