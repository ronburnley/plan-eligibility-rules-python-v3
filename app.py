from flask import Flask, render_template, request, jsonify
from plan_eligibility import evaluate_plan

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
        puf_file = "business-rules-puf 2.csv"

        criteria = evaluate_plan(api_key, plan_id, zip_code, year, puf_file)
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