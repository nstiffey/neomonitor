import os
import logging
from flask import Flask, jsonify, request
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database Config
DATABASE_URL = os.environ.get('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    risk_threshold_km = Column(Float, default=1000000.0)

class Watchlist(Base):
    __tablename__ = "watchlist_entries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    asteroid_id = Column(String, index=True)
    name = Column(String)
    close_approach_date = Column(String)
    miss_distance_km = Column(Float)

# --- Startup Logic (Create Tables) ---
def init_db():
    try:
        # Create Tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

# Run initialization once on import
init_db()

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json() or {}
    name = data.get('name')
    threshold = float(data.get('risk_threshold_km', 1000000.0))

    if not name:
        return jsonify({'error': 'name is required'}), 400

    db = SessionLocal()
    existing = db.query(User).filter(User.name == name).first()
    if existing:
        db.close()
        return jsonify({'error': 'User already exists'}), 409

    user = User(name=name, risk_threshold_km=threshold)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    return jsonify({'id': user.id, 'name': user.name, 'risk_threshold_km': user.risk_threshold_km}), 201


@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id": user.id,
        "name": user.name,
        "risk_threshold_km": user.risk_threshold_km
    })


@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.close()
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        user.name = data['name']
    if 'risk_threshold_km' in data:
        user.risk_threshold_km = float(data['risk_threshold_km'])

    db.commit()
    updated = {
        'id': user.id,
        'name': user.name,
        'risk_threshold_km': user.risk_threshold_km
    }
    db.close()
    return jsonify(updated), 200


@app.route('/users/<int:user_id>/watchlist', methods=['GET'])
def get_watchlist(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.close()
        return jsonify({'error': 'User not found'}), 404

    query = db.query(Watchlist).filter(Watchlist.user_id == user_id)
    asteroid_id = request.args.get('id') or request.args.get('search_id')
    if asteroid_id:
        query = query.filter(Watchlist.asteroid_id.ilike(f"%{asteroid_id}%"))

    sort_by = request.args.get('sort_by')
    order = request.args.get('order', 'asc').lower()
    if sort_by in ['date', 'miss_distance']:
        if sort_by == 'date':
            sort_column = Watchlist.close_approach_date
        else:
            sort_column = Watchlist.miss_distance_km

        if order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    entries = query.all()

    response = {
        'user_id': user.id,
        'user_name': user.name,
        'risk_threshold_km': user.risk_threshold_km,
        'watchlist': [],
        'total_count': len(entries)
    }

    for entry in entries:
        response['watchlist'].append({
            'id': entry.asteroid_id,
            'name': entry.name,
            'date': entry.close_approach_date,
            'miss_distance_km': entry.miss_distance_km,
            'within_threshold': entry.miss_distance_km <= user.risk_threshold_km
        })

    db.close()
    return jsonify(response), 200


@app.route('/users/<int:user_id>/watchlist', methods=['POST'])
def add_watchlist_entry(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.close()
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}
    asteroid_id = data.get('id')
    name = data.get('name', '')
    date = data.get('date')
    miss_distance = data.get('miss_distance_km')

    if not asteroid_id or date is None or miss_distance is None:
        db.close()
        return jsonify({'error': 'id, date, and miss_distance_km are required'}), 400

    existing = db.query(Watchlist).filter(
        Watchlist.user_id == user_id,
        Watchlist.asteroid_id == asteroid_id
    ).first()

    if existing:
        existing.name = name
        existing.close_approach_date = date
        existing.miss_distance_km = float(miss_distance)
        db.commit()
        result = existing
        status_code = 200
    else:
        result = Watchlist(
            user_id=user_id,
            asteroid_id=asteroid_id,
            name=name,
            close_approach_date=date,
            miss_distance_km=float(miss_distance)
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        status_code = 201

    resp = {
        'user_id': user_id,
        'asteroid_id': result.asteroid_id,
        'name': result.name,
        'date': result.close_approach_date,
        'miss_distance_km': result.miss_distance_km,
        'within_threshold': result.miss_distance_km <= user.risk_threshold_km
    }

    db.close()
    return jsonify(resp), status_code


@app.route('/users/<int:user_id>/watchlist/<string:asteroid_id>', methods=['DELETE'])
def delete_watchlist_entry(user_id, asteroid_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.close()
        return jsonify({'error': 'User not found'}), 404

    entry = db.query(Watchlist).filter(
        Watchlist.user_id == user_id,
        Watchlist.asteroid_id == asteroid_id
    ).first()

    if not entry:
        db.close()
        return jsonify({'error': 'Entry not found'}), 404

    db.delete(entry)
    db.commit()
    db.close()
    return jsonify({'message': 'Entry removed'}), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)