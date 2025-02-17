import requests
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import date, datetime

@dataclass
class PlanEligibilityCriteria:
    eligible_dependents: List[str]
    maximum_dependent_age: int
    plan_type: str
    service_area: str
    tobacco_use_rules: str
    market_coverage: str
    dental_coverage: bool
    is_eligible: bool
    eligibility_reasons: List[str]
    tobacco_status: str

class PlanEligibilityEvaluator:
    def __init__(self, api_key: str, puf_file_path: str):
        """
        Initialize the evaluator with API key and path to PUF file
        
        Args:
            api_key: CMS Marketplace API key
            puf_file_path: Path to the business rules PUF CSV file
        """
        self.api_key = api_key
        self.puf_file_path = puf_file_path
        self.puf_data = pd.read_csv(puf_file_path)
        self.api_base_url = "https://marketplace.api.healthcare.gov/api/v1"

    def get_plan_details(self, plan_id: str, zip_code: str, year: int) -> Dict:
        """
        Retrieve plan details from CMS API
        
        Args:
            plan_id: Plan identifier
            zip_code: ZIP code for service area check
            year: Plan year
            
        Returns:
            Dict containing plan details from API
        """
        headers = {
            "apikey": self.api_key
        }
        
        url = f"{self.api_base_url}/plans/{plan_id}?year={year}&zipcode={zip_code}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to retrieve plan details: {str(e)}")

    def get_plan_rules(self, plan_id: str, year: int) -> Optional[pd.Series]:
        """
        Get business rules for a specific plan from PUF file
        
        Args:
            plan_id: Plan identifier
            year: Plan year
            
        Returns:
            Series containing plan rules or None if not found
        """
        mask = (self.puf_data['BusinessYear'] == year) & \
               (self.puf_data['StandardComponentId'] == plan_id)
        
        matching_rules = self.puf_data[mask]
        
        if matching_rules.empty:
            return None
            
        return matching_rules.iloc[0]

    def calculate_age(self, birth_date: date) -> int:
        """Calculate age from birth date."""
        today = date.today()
        age = today.year - birth_date.year
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
        return age

    def evaluate_eligibility(self, plan_id: str, zip_code: str, year: str, applicant_dob: date, 
                           income: float, dependents: List[Dict[str, Any]],
                           never_used_tobacco: bool = False, last_tobacco_use_date: Optional[date] = None) -> PlanEligibilityCriteria:
        """Evaluate eligibility criteria for a given plan."""
        # Get data from both sources
        api_data = self.get_plan_details(plan_id, zip_code, year)
        puf_rules = self.get_plan_rules(plan_id, year)
        
        if puf_rules is None:
            raise Exception(f"Plan {plan_id} not found in PUF file for year {year}")
        
        # Extract data from API response
        plan_data = api_data.get('plan', {})
        
        # Validate plan details against PUF rules
        api_market = plan_data.get('market', '').upper()
        puf_market = str(puf_rules.get('MarketCoverage', '')).upper().strip()
        if api_market and puf_market and api_market != puf_market:
            raise Exception(f"Market coverage mismatch: API reports {api_market}, PUF file reports {puf_market}")
            
        api_plan_type = plan_data.get('type', '').upper()
        puf_plan_type = str(puf_rules.get('PlanType', '')).upper().strip()
        if api_plan_type and puf_plan_type:
            # Map common plan type variations
            plan_type_mapping = {
                'EPO': ['EPO', 'EXCLUSIVE PROVIDER ORGANIZATION'],
                'HMO': ['HMO', 'HEALTH MAINTENANCE ORGANIZATION'],
                'PPO': ['PPO', 'PREFERRED PROVIDER ORGANIZATION'],
                'POS': ['POS', 'POINT OF SERVICE']
            }
            
            # Normalize plan types using the mapping
            api_normalized = None
            puf_normalized = None
            
            for standard_type, variations in plan_type_mapping.items():
                if api_plan_type in variations:
                    api_normalized = standard_type
                if puf_plan_type in variations:
                    puf_normalized = standard_type
            
            if api_normalized and puf_normalized and api_normalized != puf_normalized:
                raise Exception(f"Plan type mismatch: API reports {api_plan_type}, PUF file reports {puf_plan_type}")

        # Evaluate applicant eligibility
        eligibility_reasons = []
        is_eligible = True

        # Check applicant age
        applicant_age = self.calculate_age(applicant_dob)
        if applicant_age < 18:
            is_eligible = False
            eligibility_reasons.append("Applicant must be at least 18 years old")

        # Check income requirements
        min_income = float(puf_rules.get('MinimumMonthlyPremium', 0)) * 12
        if income < min_income:
            is_eligible = False
            eligibility_reasons.append(f"Income must be at least ${min_income:,.2f} annually")

        # Check tobacco usage rules
        tobacco_lookback = plan_data.get('tobacco_lookback')
        if tobacco_lookback is not None:
            if not never_used_tobacco and last_tobacco_use_date:
                # Calculate months since last tobacco use
                today = date.today()
                months_since_tobacco = (today.year - last_tobacco_use_date.year) * 12 + (today.month - last_tobacco_use_date.month)
                
                if months_since_tobacco < tobacco_lookback:
                    is_eligible = False
                    eligibility_reasons.append(f"Must be tobacco-free for at least {tobacco_lookback} months (currently {months_since_tobacco} months)")
            elif not never_used_tobacco and not last_tobacco_use_date:
                eligibility_reasons.append("Tobacco usage information required for this plan")

        # Check dependent eligibility
        max_dependent_age = plan_data.get('max_age_child', 26)
        allowed_relationships = set(['spouse', 'child', 'adopted_child'])
        
        for dependent in dependents:
            dependent_age = self.calculate_age(dependent['date_of_birth'])
            relationship = dependent['relationship']

            if relationship not in allowed_relationships:
                if relationship in ['brother', 'sister', 'grandparent']:
                    is_eligible = False
                    eligibility_reasons.append(f"{relationship.capitalize()} is not an eligible dependent type for this plan")
            
            if relationship in ['child', 'adopted_child'] and dependent_age > max_dependent_age:
                is_eligible = False
                eligibility_reasons.append(f"Dependent children must be under {max_dependent_age} years old")

        # If no specific reasons for ineligibility were found
        if is_eligible:
            eligibility_reasons.append("All eligibility criteria met")
        
        # Extract other plan details
        service_area = plan_data.get('service_area_id', 'Not specified')
        market = plan_data.get('market', 'Not specified')
        
        # Format tobacco rules message
        tobacco_rules = "Not specified"
        if tobacco_lookback is not None:
            tobacco_rules = f"Must be tobacco-free for {tobacco_lookback} months"
        
        return PlanEligibilityCriteria(
            eligible_dependents=plan_data.get('issuer', {}).get('eligible_dependents', ['Not specified']),
            maximum_dependent_age=max_dependent_age,
            plan_type=plan_data.get('type', 'Not specified'),
            service_area=service_area,
            tobacco_use_rules=tobacco_rules,
            market_coverage=market,
            dental_coverage=any(b.get('covered', False) for b in plan_data.get('benefits', []) if 'DENTAL' in b.get('type', '')),
            is_eligible=is_eligible,
            eligibility_reasons=eligibility_reasons,
            tobacco_status="Never used tobacco" if never_used_tobacco else f"Last used tobacco on {last_tobacco_use_date}" if last_tobacco_use_date else "Not specified"
        )

    def format_eligibility_output(self, criteria: PlanEligibilityCriteria) -> List[str]:
        """
        Format eligibility criteria into bullet points
        
        Args:
            criteria: PlanEligibilityCriteria object
            
        Returns:
            List of formatted bullet points
        """
        # Start with eligibility status
        bullets = [
            f"* Eligibility Status: {'ELIGIBLE' if criteria.is_eligible else 'NOT ELIGIBLE'}",
            f"* Eligibility Details: {'; '.join(criteria.eligibility_reasons)}"
        ]

        # Add plan details
        bullets.extend([
            f"* Eligible dependents: {', '.join(criteria.eligible_dependents)}",
            f"* Maximum dependent age: {criteria.maximum_dependent_age if criteria.maximum_dependent_age > 0 else 'Not Applicable'}" + 
            (" (extends beyond standard age 26)" if criteria.maximum_dependent_age > 26 else ""),
            f"* Plan type: {criteria.plan_type}",
            f"* Service area: {criteria.service_area}",
            f"* Tobacco use rules: {criteria.tobacco_use_rules}",
            f"* Market coverage: {criteria.market_coverage}",
            f"* Dental coverage: {'Yes' if criteria.dental_coverage else 'No'}",
            f"* Tobacco status: {criteria.tobacco_status}"
        ])
        
        return bullets

def evaluate_plan(api_key: str, plan_id: str, zip_code: str, year: int, puf_file_path: str,
                 applicant_dob: date, income: float, dependents: List[Dict[str, Any]], 
                 never_used_tobacco: bool = False, last_tobacco_use_date: Optional[date] = None) -> List[str]:
    """
    Convenience function to evaluate plan eligibility in one call
    
    Args:
        api_key: CMS Marketplace API key
        plan_id: Plan identifier
        zip_code: ZIP code for service area check
        year: Plan year
        puf_file_path: Path to business rules PUF file
        applicant_dob: Applicant's date of birth
        income: Annual household income
        dependents: List of dependent information (date of birth and relationship)
        never_used_tobacco: Whether the applicant has never used tobacco
        last_tobacco_use_date: Date of last tobacco use if applicable
        
    Returns:
        List of formatted eligibility criteria bullet points
    """
    evaluator = PlanEligibilityEvaluator(api_key, puf_file_path)
    criteria = evaluator.evaluate_eligibility(
        plan_id, zip_code, year, applicant_dob, income, dependents,
        never_used_tobacco, last_tobacco_use_date
    )
    return evaluator.format_eligibility_output(criteria) 