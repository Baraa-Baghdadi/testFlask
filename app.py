from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import datetime
import os
from functools import wraps

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
DATABASE = 'project_status.db'
SECRET_TOKEN = 'your-super-secret-token-2024'  # Change this in production
ADMIN_TOKEN = 'admin-secret-token-2024'        # Change this in production

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database with sample data"""
    conn = get_db_connection()
    
    # Create projects table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            last_checked DATETIME,
            notes TEXT
        )
    ''')
    
    # Create access logs table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            ip_address TEXT,
            user_agent TEXT,
            access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (project_id)
        )
    ''')
    
    # Insert sample projects
    sample_projects = [
        {
            'project_id': 'proj_001_website',
            'client_name': 'TTech',
            'is_active': True,
            'notes': 'Dawaa24'
        },
        {
            'project_id': 'proj_002_app',
            'client_name': 'TTech',
            'is_active': False,
            'notes': 'Provider Portal'
        },
        {
            'project_id': 'proj_003_dashboard',
            'client_name': 'TTech',
            'is_active': True,
            'notes': 'Pharmacy Portal'
        }
    ]
    
    for project in sample_projects:
        try:
            conn.execute('''
                INSERT OR IGNORE INTO projects 
                (project_id, client_name, is_active, notes)
                VALUES (?, ?, ?, ?)
            ''', (
                project['project_id'],
                project['client_name'],
                project['is_active'],
                project['notes']
            ))
        except sqlite3.IntegrityError:
            pass  # Project already exists
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def require_auth(token_type='client'):
    """Decorator for authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({
                    'success': False,
                    'message': 'Missing or invalid authorization header'
                }), 401
            
            token = auth_header.split(' ')[1]
            
            if token_type == 'admin' and token != ADMIN_TOKEN:
                return jsonify({
                    'success': False,
                    'message': 'Invalid admin token'
                }), 401
            elif token_type == 'client' and token != SECRET_TOKEN:
                return jsonify({
                    'success': False,
                    'message': 'Invalid client token'
                }), 401
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_access(project_id, status):
    """Log access attempt"""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO access_logs (project_id, ip_address, user_agent, status)
        VALUES (?, ?, ?, ?)
    ''', (
        project_id,
        request.remote_addr,
        request.headers.get('User-Agent', 'Unknown'),
        status
    ))
    conn.commit()
    conn.close()

# ================================
# API Routes
# ================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'License server is running',
        'timestamp': datetime.datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/validate/<project_id>', methods=['GET'])
@require_auth('client')
def validate_project(project_id):
    """Validate project license"""
    try:
        conn = get_db_connection()
        
        # Update last checked time
        conn.execute('''
            UPDATE projects 
            SET last_checked = CURRENT_TIMESTAMP 
            WHERE project_id = ?
        ''', (project_id,))
        
        # Get project details
        project = conn.execute('''
            SELECT * FROM projects WHERE project_id = ?
        ''', (project_id,)).fetchone()
        
        conn.commit()
        conn.close()
        
        if not project:
            log_access(project_id, 'PROJECT_NOT_FOUND')
            return jsonify({
                'success': False,
                'message': 'Project not found'
            }), 404
        
        # Check if project is active
        if not project['is_active']:
            log_access(project_id, 'PROJECT_NOT_ACTIVE')
            return jsonify({
                'success': False,
                'message': 'Project is not active'
            }), 403
        
        log_access(project_id, 'VALID_ACCESS')
        
        return jsonify({
            'success': True,
            'message': 'Project license is active',
            'data': {
                'project_id': project['project_id'],
                'client_name': project['client_name'],
                'is_active': bool(project['is_active']),
                'status': 'active' if project['is_active'] else 'not active',
                'last_checked': project['last_checked']
            }
        })
        
    except Exception as e:
        log_access(project_id, 'ERROR')
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/projects', methods=['GET'])
@require_auth('admin')
def list_projects():
    """List all projects (Admin only)"""
    try:
        conn = get_db_connection()
        projects = conn.execute('''
            SELECT * FROM projects ORDER BY id DESC
        ''').fetchall()
        conn.close()
        
        projects_list = []
        for project in projects:
            projects_list.append({
                'id': project['id'],
                'project_id': project['project_id'],
                'client_name': project['client_name'],
                'is_active': bool(project['is_active']),
                'status': 'active' if project['is_active'] else 'not active',
                'last_checked': project['last_checked'],
                'notes': project['notes']
            })
        
        return jsonify({
            'success': True,
            'data': projects_list,
            'count': len(projects_list)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/projects/<project_id>', methods=['PUT'])
@require_auth('admin')
def update_project_status(project_id):
    """Update project status (Admin only)"""
    try:
        data = request.get_json()
        is_active = data.get('is_active')
        notes = data.get('notes')
        
        conn = get_db_connection()
        
        # Check if project exists
        project = conn.execute('''
            SELECT * FROM projects WHERE project_id = ?
        ''', (project_id,)).fetchone()
        
        if not project:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Project not found'
            }), 404
        
        # Update project
        update_fields = []
        params = []
        
        if is_active is not None:
            update_fields.append('is_active = ?')
            params.append(is_active)
            
        if notes is not None:
            update_fields.append('notes = ?')
            params.append(notes)
        
        if update_fields:
            params.append(project_id)
            query = f"UPDATE projects SET {', '.join(update_fields)} WHERE project_id = ?"
            conn.execute(query, params)
            conn.commit()
        
        # Get updated project
        updated_project = conn.execute('''
            SELECT * FROM projects WHERE project_id = ?
        ''', (project_id,)).fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Project updated successfully',
            'data': {
                'project_id': updated_project['project_id'],
                'client_name': updated_project['client_name'],
                'is_active': bool(updated_project['is_active']),
                'status': 'active' if updated_project['is_active'] else 'not active',
                'notes': updated_project['notes']
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/projects', methods=['POST'])
@require_auth('admin')
def create_project():
    """Create new project (Admin only)"""
    try:
        data = request.get_json()
        
        required_fields = ['project_id', 'client_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        conn = get_db_connection()
        
        conn.execute('''
            INSERT INTO projects (project_id, client_name, is_active, notes)
            VALUES (?, ?, ?, ?)
        ''', (
            data['project_id'],
            data['client_name'],
            data.get('is_active', True),
            data.get('notes', '')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Project created successfully',
            'data': {
                'project_id': data['project_id'],
                'client_name': data['client_name'],
                'is_active': data.get('is_active', True),
                'status': 'active' if data.get('is_active', True) else 'not active'
            }
        }), 201
        
    except sqlite3.IntegrityError:
        return jsonify({
            'success': False,
            'message': 'Project ID already exists'
        }), 409
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/logs/<project_id>', methods=['GET'])
@require_auth('admin')
def get_project_logs(project_id):
    """Get access logs for a project (Admin only)"""
    try:
        conn = get_db_connection()
        logs = conn.execute('''
            SELECT * FROM access_logs 
            WHERE project_id = ? 
            ORDER BY access_time DESC 
            LIMIT 100
        ''', (project_id,)).fetchall()
        conn.close()
        
        logs_list = []
        for log in logs:
            logs_list.append({
                'id': log['id'],
                'project_id': log['project_id'],
                'ip_address': log['ip_address'],
                'user_agent': log['user_agent'],
                'access_time': log['access_time'],
                'status': log['status']
            })
        
        return jsonify({
            'success': True,
            'data': logs_list,
            'count': len(logs_list)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

# ================================
# Error Handlers
# ================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error'
    }), 500

# ================================
# Main Execution
# ================================

if __name__ == '__main__':
    print("🚀 Starting Flask License Server...")
    print("📁 Initializing database...")
    
    # Initialize database
    init_database()
    
    print("\n" + "="*50)
    print("📋 API ENDPOINTS:")
    print("="*50)
    print("🔍 Health Check:")
    print("   GET  /api/health")
    print("\n🔐 Client Endpoints (Token: your-super-secret-token-2024):")
    print("   GET  /api/validate/<project_id>")
    print("\n👨‍💼 Admin Endpoints (Token: admin-secret-token-2024):")
    print("   GET  /api/projects")
    print("   POST /api/projects")
    print("   PUT  /api/projects/<project_id>")
    print("   GET  /api/logs/<project_id>")
    print("\n📝 Sample Project IDs:")
    print("   - proj_001_website (Active)")
    print("   - proj_002_app (Not Active)")
    print("   - proj_003_dashboard (Active)")
    print("="*50)
    print("\n🌐 Server starting on http://localhost:5000")
    print("💡 Use Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
