from flask import Flask, render_template, request, jsonify
from plan_eligibility import evaluate_plan
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/evaluate', methods=['POST'])
def evaluate():
    try:
        data = request.json
        api_key = data.get('api_key')
        plan_id = data.get('plan_id')
        zip_code = data.get('zip_code')
        year = int(data.get('year'))
        applicant_dob = datetime.strptime(data.get('applicant_dob'), '%Y-%m-%d').date()
        income = float(data.get('income'))
        dependents = data.get('dependents', [])
        never_used_tobacco = data.get('never_used_tobacco', False)
        last_tobacco_use = data.get('last_tobacco_use')
        
        # Convert last tobacco use date if provided
        last_tobacco_use_date = None
        if last_tobacco_use and not never_used_tobacco:
            last_tobacco_use_date = datetime.strptime(last_tobacco_use, '%Y-%m-%d').date()
        
        # Convert dependent dates to date objects
        for dependent in dependents:
            dependent['date_of_birth'] = datetime.strptime(dependent['date_of_birth'], '%Y-%m-%d').date()
        
        puf_file = "business-rules-puf 2.csv"

        criteria = evaluate_plan(
            api_key=api_key,
            plan_id=plan_id,
            zip_code=zip_code,
            year=year,
            puf_file_path=puf_file,
            applicant_dob=applicant_dob,
            income=income,
            dependents=dependents,
            never_used_tobacco=never_used_tobacco,
            last_tobacco_use_date=last_tobacco_use_date
        )
        
        return jsonify({
            'success': True,
            'criteria': criteria
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

if __name__ == '__main__':
    app.run(debug=True) 