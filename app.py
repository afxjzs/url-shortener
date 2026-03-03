"""URL Shortener redirect service."""
import os
import logging
import functools
import qrcode
import io
from datetime import datetime
from flask import Flask, redirect, request, jsonify, send_file
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import NoResultFound, IntegrityError
from dotenv import load_dotenv
from models import Base, Shortcode, Click
from cryptography.fernet import Fernet
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost/url_shortener'
)
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)

# Create tables if they don't exist (only if not testing)
if not os.getenv('TESTING'):
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        logger.warning(f"Could not create tables on startup: {e}")

# Flask app
app = Flask(__name__)
csrf = CSRFProtect(app)

# Disable rate limiting in test mode
if os.getenv('TESTING'):
    limiter = Limiter(key_func=get_remote_address, app=app, enabled=False)
else:
    limiter = Limiter(key_func=get_remote_address, app=app, default_limits=['100 per hour'])

# Configure Flask
app.config.update(
    JSON_SORT_KEYS=False,
    SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
    WTF_CSRF_ENABLED=True
)

# Encryption setup
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'u1Zk5M4Z3C1X2V5B7N9Q0W8E4R6T7Y9U1A2S3D5F=')
try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
except Exception as e:
    logger.warning(f"Encryption key invalid, using unencrypted IP storage: {e}")
    cipher_suite = None


def encrypt_ip(ip_str: str) -> str:
    """Encrypt IP address using Fernet."""
    if not cipher_suite:
        return ip_str
    try:
        return cipher_suite.encrypt(ip_str.encode()).decode()
    except Exception as e:
        logger.error(f"IP encryption failed: {e}")
        return ip_str


def decrypt_ip(encrypted_ip: str) -> str:
    """Decrypt IP address."""
    if not cipher_suite:
        return encrypted_ip
    try:
        return cipher_suite.decrypt(encrypted_ip.encode()).decode()
    except Exception as e:
        logger.error(f"IP decryption failed: {e}")
        return encrypted_ip


@functools.lru_cache(maxsize=128)
def generate_qr_code(shortcode: str) -> bytes:
    """Generate QR code for shortcode (cached)."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f'http://l.afx.cc/{shortcode}')
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io.getvalue()


@app.route('/<shortcode>', methods=['GET'])
@limiter.limit('100 per hour')
def redirect_shortcode(shortcode: str):
    """Redirect to target URL and log the click."""
    session = Session()
    try:
        # Find shortcode
        short = session.query(Shortcode).filter(
            Shortcode.shortcode == shortcode,
            Shortcode.active == True
        ).first()

        if not short:
            logger.warning(f"Shortcode not found: {shortcode}")
            return jsonify({'error': 'Shortcode not found'}), 404

        # Log click
        user_agent = request.headers.get('User-Agent', '')
        referer = request.headers.get('Referer', '')
        ip_address = request.remote_addr or 'unknown'
        
        click = Click(
            shortcode_id=short.id,
            timestamp=datetime.utcnow(),
            ip_address=encrypt_ip(ip_address),
            user_agent=user_agent,
            referer=referer,
            country=None,
            city=None
        )
        
        try:
            session.add(click)
            session.commit()
            logger.info(f"Click logged for {shortcode} from {ip_address}")
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Database integrity error: {e}")
            return jsonify({'error': 'Failed to log click'}), 500
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            return jsonify({'error': 'Internal server error'}), 500

        # Redirect
        return redirect(short.target_url, code=302)

    except NoResultFound:
        return jsonify({'error': 'Shortcode not found'}), 404
    except Exception as e:
        logger.error(f"Redirect error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@app.route('/qr/<shortcode>', methods=['GET'])
def get_qr_code(shortcode: str):
    """Generate and return QR code for shortcode."""
    session = Session()
    try:
        # Verify shortcode exists
        short = session.query(Shortcode).filter(
            Shortcode.shortcode == shortcode
        ).first()

        if not short:
            logger.warning(f"QR code requested for non-existent shortcode: {shortcode}")
            return jsonify({'error': 'Shortcode not found'}), 404

        # Generate QR code (cached)
        qr_bytes = generate_qr_code(shortcode)
        img_io = io.BytesIO(qr_bytes)

        return send_file(img_io, mimetype='image/png', as_attachment=False)

    except NoResultFound:
        return jsonify({'error': 'Shortcode not found'}), 404
    except Exception as e:
        logger.error(f"QR code generation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200


@app.route('/stats/<shortcode>', methods=['GET'])
def get_stats(shortcode: str):
    """Get click stats for a shortcode."""
    session = Session()
    try:
        short = session.query(Shortcode).filter(
            Shortcode.shortcode == shortcode
        ).first()

        if not short:
            return jsonify({'error': 'Shortcode not found'}), 404

        clicks = session.query(Click).filter(Click.shortcode_id == short.id).all()
        click_count = len(clicks)

        return jsonify({
            'shortcode': shortcode,
            'target_url': short.target_url,
            'click_count': click_count,
            'created_at': short.created_at.isoformat(),
            'active': short.active
        }), 200

    except NoResultFound:
        return jsonify({'error': 'Shortcode not found'}), 404
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@app.errorhandler(429)
def rate_limit_handler(e):
    """Handle rate limit exceeded."""
    logger.warning(f"Rate limit exceeded: {request.remote_addr}")
    return jsonify({'error': 'Rate limit exceeded'}), 429


@app.errorhandler(404)
def not_found(e):
    """Handle 404."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500."""
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logger.info("Starting URL Shortener service...")
    app.run(host='0.0.0.0', port=5000, debug=False)
