import os
from flask import Flask, request, Response, redirect
from github import GithubIntegration
from dotenv import load_dotenv
import logging

from github_functions.handle_new_pr import handle_new_pr
from github_functions.handle_new_comment import handle_new_comment
import hmac
import hashlib
import base64
from schemas import db, User
import requests

load_dotenv()



perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
ai_fixed_code_list = []
ai_fixed_code = ""

app_id = os.getenv("APP_ID")

github_private_key_base64 = os.environ.get('PRIVATE_KEY_BASE64')
github_private_key = base64.b64decode(github_private_key_base64).decode('utf-8')
app_key = github_private_key
git_integration = GithubIntegration(
    app_id,
    app_key, 
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def is_valid_signature(signature, payload, secret):
    if not secret:
        logger.error("Webhook secret is not set")
        return False
    if not signature:
        logger.error("X-Hub-Signature-256 header is missing")
        return False
    try:
        expected_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    except Exception as e:
        logger.error(f"Error validating signature: {str(e)}")
        return False

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres.iggamyayazhlsqmbdoyj:BUqr5ek4aGqEyqWp@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    app.secret_key = os.getenv('FLASK_SECRET_KEY') 
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


   
    # Initialize the app with the database
    db.init_app(app)

    with app.app_context():
        db.create_all()


    @app.route("/callback")
    def callback():
        code = request.args.get("code")

        if code:
            try:
                # Exchange code for access token
                response = requests.post(
                    'https://github.com/login/oauth/access_token',
                    headers={'Accept': 'application/json'},
                    data={
                        'client_id': os.getenv('GITHUB_CLIENT_ID'),
                        'client_secret': os.getenv('GITHUB_CLIENT_SECRET'),
                        'code': code
                    }
                )
                access_token = response.json().get('access_token')
                print(access_token)

                # Get user information using the access token
                user_response = requests.get(
                    'https://api.github.com/user',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Accept': 'application/json'
                    }
                )
                user_data = user_response.json()
                # print(user_data)
                # Create user record
                existing_user = User.query.filter_by(username=user_data.get('login')).first()
                if existing_user:
                    existing_user.access_token = access_token
                    db.session.commit()
                    user = existing_user
                else:
                    user = User(
                        username=user_data.get('login'),
                        access_token=access_token
                    )
                    db.session.add(user)
                    db.session.commit()
                
                # Log the user in
                logger.info(f"User {user.username} logged in successfully")
                
                return redirect("https://github.com/apps/prReviewer/installations/new")
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}", exc_info=True)
                return Response("Internal server error", status=500)


    
    @app.route("/", methods=['POST'])
    
    def bot():
        try:
            

            # Verify webhook signature
            signature = request.headers.get('X-Hub-Signature-256')
            webhook_secret = os.getenv('GITHUB_WEBHOOK_SECRET')
            if not is_valid_signature(signature, request.data, webhook_secret):
                print(f"Invalid signature received: {signature}")
                
                print(f"Webhook secret: {webhook_secret}")
                # print(f"Request data: {request.data}")
                logger.warning("Invalid signature received")
                return "Invalid signature", 403
            
            payload = request.json
            if payload.get('action') == 'opened' and 'pull_request' in payload:
                logger.info("Handling new pull request")
                return handle_new_pr(payload)
            elif payload.get('action') == 'created' and 'comment' in payload and 'issue' in payload and 'pull_request' in payload['issue']:
                logger.info("Handling new comment")
                return handle_new_comment(payload)
            else:
                logger.info("Received unhandled webhook event")
            return "ok"
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}", exc_info=True)
            return Response("Internal server error", status=500)

    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True, threaded=True)
