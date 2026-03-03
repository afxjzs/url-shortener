"""URL Shortener redirect service."""
import os
import base64
import qrcode
import io
from datetime import datetime
from flask import Flask, redirect, request, jsonify, send_file
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import Base, Shortcode, Click

# Load environment variables
load_dotenv()

# Database setup
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost/url_shortener'
)
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)

# Create tables if they don't exist
Base.metadata.create_all(engine)

# Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


def get_ip_base64(ip_str):
    """Encode IP address as base64."""
    return base64.b64encode(ip_str.encode()).decode()


def decode_ip_base64(encoded_ip):
    """Decode base64 IP address."""
    try:
        return base64.b64decode(encoded_ip).decode()
    except Exception:
        return encoded_ip


@app.route('/<shortcode>', methods=['GET'])
def redirect_shortcode(shortcode):
    """Redirect to target URL and log the click."""
    session = Session()
    try:
        # Find shortcode
        short = session.query(Shortcode).filter(
            Shortcode.shortcode == shortcode,
            Shortcode.active == True
        ).first()

        if not short:
            return jsonify({'error': 'Shortcode not found'}), 404

        # Log click
        user_agent = request.headers.get('User-Agent', '')
        referer = request.headers.get('Referer', '')
        ip_address = request.remote_addr or 'unknown'
        
        # Get country/city from IP (optional - can enhance later)
        country = None
        city = None

        click = Click(
            shortcode_id=short.id,
            timestamp=datetime.utcnow(),
            ip_address=get_ip_base64(ip_address),
            user_agent=user_agent,
            referer=referer,
            country=country,
            city=city
        )
        session.add(click)
        session.commit()

        # Redirect
        return redirect(short.target_url, code=302)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@app.route('/qr/<shortcode>', methods=['GET'])
def get_qr_code(shortcode):
    """Generate and return QR code for shortcode."""
    session = Session()
    try:
        # Find shortcode
        short = session.query(Shortcode).filter(
            Shortcode.shortcode == shortcode
        ).first()

        if not short:
            return jsonify({'error': 'Shortcode not found'}), 404

        # Generate QR code pointing to the redirect URL
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f'http://l.afx.cc/{shortcode}')
        qr.make(fit=True)

        img = qr.make_image(fill_color='black', back_color='white')
        
        # Return as PNG
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200


@app.route('/stats/<shortcode>', methods=['GET'])
def get_stats(shortcode):
    """Get click stats for a shortcode (basic)."""
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

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


if __name__ == '__main__':
    # Run development server
    app.run(host='0.0.0.0', port=5000, debug=True)
