import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.agendamento import agendamento_bp
from src.routes.mensagem import mensagem_bp
from src.routes.documento import documento_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string-change-in-production'

# Configurar CORS para permitir requisições do frontend
CORS(app, origins="*")

# Configurar JWT
jwt = JWTManager(app)

# Registrar blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(agendamento_bp, url_prefix='/api')
app.register_blueprint(mensagem_bp, url_prefix='/api')
app.register_blueprint(documento_bp, url_prefix='/api')

# Configurar banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Criar tabelas e dados iniciais
with app.app_context():
    db.create_all()
    
    # Criar usuário médica padrão se não existir
    from src.models.user import User
    medica = User.query.filter_by(role='medica').first()
    if not medica:
        medica = User(
            username='dra_pediatra',
            email='dra@pediatra.com.br',
            nome_completo='Dra. [Nome da Médica]',
            telefone='(11) 99999-9999',
            role='medica'
        )
        medica.set_password('senha123')
        db.session.add(medica)
        db.session.commit()
        print("Usuário médica criado: username=dra_pediatra, senha=senha123")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

@app.route('/api/health', methods=['GET'])
def health_check():
    return {'status': 'OK', 'message': 'API funcionando corretamente'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
